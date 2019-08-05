# -*- coding: utf-8 -*-
"""\
PyMzn provides an interface to the ``minizinc`` executable to compile a MiniZinc
model into a FlatZinc one, solve a given problem and get back the resulting
solutions directly as Python objects.

The main function that PyMzn provides is the ``pymzn.minizinc`` function, which
executes the entire workflow for solving a constranint program encoded in
MiniZinc, just like using the ``minizinc`` executable from command line. As
added benefit, the ``pymzn.minizinc`` function takes care of adding
solver-dependent parameters and converts the solutions into Python dictionaries
by default. Solving a MiniZinc problem with PyMzn is as simple as:

.. code-block:: python3

    import pymzn
    pymzn.minizinc('test.mzn')

The ``pymzn.minizinc`` function is probably the way to go for most of the
problems, but the ``pymzn.mzn2fzn`` and ``pymzn.solns2out`` functions are also
included in the library to allow for maximum flexibility. The latter two
functions are wrappers of the two homonym MiniZinc tools for, respectively,
converting a MiniZinc model into a FlatZinc one and getting custom output from
the solution stream of a solver.
"""

import os
import re
import json
import contextlib

from time import monotonic as _time
from tempfile import NamedTemporaryFile

from .. import config, dict2dzn, logger

from .rewrap import rewrap_model
from .solvers import gecode
from .process import run_process

from . import output
from .output import *
from .output import SolutionParser


__all__ = [
    'minizinc_version', 'preprocess_model', 'save_model', 'check_model',
    'check_instance', 'minizinc', 'solve', 'mzn2fzn', 'solns2out',
    'MiniZincError'
] + output.__all__


def _run_minizinc_proc(*args, input=None):
    logger.debug('Executing minizinc with arguments: {}'.format(args))
    args = [config.minizinc] + list(args)
    return run_process(*args, input=input)


def _run_minizinc(*args, input=None):
    proc = _run_minizinc_proc(*args, input=input)
    return proc.stdout_data


def minizinc_version():
    """Returns the version of the found minizinc executable."""
    vs = _run_minizinc('--version')
    m = re.findall('version ([\d\.]+)', vs)
    if not m:
        raise RuntimeError('MiniZinc executable not found.')
    return m[0]


def check_version():
    version = minizinc_version()
    logger.info('Using MiniZinc {}.'.format(version))
    major, minor, *_ = version.split('.')
    major, minor = int(major), int(minor)
    vs = major * 100 + minor
    if vs < 202:
        raise RuntimeError('PyMzn requires MiniZinc 2.2.0 or later.')


def _process_template(model, **kwargs):
    from .templates import from_string
    return from_string(model, kwargs)


def _var_types(mzn, allow_multiple_assignments=False):
    args = ['--model-types-only']
    if allow_multiple_assignments:
        args.append('--allow-multiple-assignments')

    input = None
    if mzn.endswith('.mzn'):
        args.append(mzn)
    else:
        args.append('-')
        input = mzn

    json_str = _run_minizinc(*args, input=input)
    var_types = json.loads(json_str)['var_types']['vars']
    logger.info('Found var types: {}'.format(var_types))
    return var_types


def _model_interface(mzn, allow_multiple_assignments=False):
    args = ['--model-interface-only']
    if allow_multiple_assignments:
        args.append('--allow-multiple-assignments')

    input = None
    if mzn.endswith('.mzn'):
        args.append(mzn)
    else:
        args.append('-')
        input = mzn

    json_str = _run_minizinc(*args, input=input)
    model_interface = json.loads(json_str)
    logger.info('Found model interface: {}'.format(model_interface))
    return model_interface


def _dzn_output_statement(output_vars, types):
    out_var = '"{0} = ", show({0}), ";\\n"'
    out_array = '"{0} = array{1}d(", {2}, ", ", show({0}), ");\\n"'
    out_list = []
    enum_types = set()
    for var in output_vars:
        if 'enum_type' in types[var]:
            enum_types.add(types[var]['enum_type'])
        if 'dim' in types[var]:
            dims = types[var]['dims']
            if len(dims) == 1:
                dim = dims[0]
                if dim != 'int':
                    enum_types.add(dim)
                    show_idx_sets = '"{}"'.format(dim)
                else:
                    show_idx_sets = 'show(index_set({}))'.format(var)
            else:
                show_idx_sets = []
                show_idx_sets_str = 'show(index_set_{}of{}({}))'
                for d in range(1, len(dims) + 1):
                    dim = dims[d - 1]
                    if dim != 'int':
                        enum_types.add(dim)
                        show_idx_sets.append(dim)
                    else:
                        show_idx_sets.append(
                            show_idx_sets_str.format(d, len(dims), var)
                        )
                show_idx_sets = ', ", ", '.join(show_idx_sets)
            out_list.append(out_array.format(var, len(dims), show_idx_sets))
        else:
            out_list.append(out_var.format(var))

    enum_list = []
    for enum_type in enum_types:
        enum_list.append(out_var.format(enum_type))

    output = ', '.join(out_list + enum_list)
    output_stmt = 'output [{}];'.format(output)
    return output_stmt


def _process_output_vars(
    model, types, output_vars=None, allow_multiple_assignments=False
):
    if output_vars is None:
        model_int = _model_interface(
            model, allow_multiple_assignments=allow_multiple_assignments
        )
        output_vars = [k for k in model_int['output']]
    output_stmt = _dzn_output_statement(output_vars, types)
    output_stmt_p_str = \
        'output\s*\[(\".+?\"|[^\"]+?)+\](\s*\+\+\s*\[(\".+?\"|[^\"]+?)+\])*\s*(?:;)?'
    output_stmt_p = re.compile(output_stmt_p_str, re.DOTALL)
    if output_stmt_p.search(model):
        logger.info(
            'Substituting model output statement: {}'.format(output_stmt))
        output_stmt = output_stmt.replace('\\', '\\\\')
        return output_stmt_p.sub(output_stmt, model)
    logger.info('Adding model output statement: {}'.format(output_stmt))
    return '\n'.join([model, output_stmt])


def preprocess_model(model, rewrap=True, **kwargs):
    """Preprocess a MiniZinc model.

    This function takes care of preprocessing the model by resolving the
    template using the arguments passed as keyword arguments to this function.
    Optionally, this function can also "rewrap" the model, deleting spaces at
    the beginning of the lines while preserving indentation.

    Parameters
    ----------
    model : str
        The minizinc model (i.e. the content of a ``.mzn`` file).
    rewrap : bool
        Whether to "rewrap" the model, i.e. to delete leading spaces, while
        preserving indentation. Default is ``True``.
    **kwargs
        Additional arguments to pass to the template engine.

    Returns
    -------
    str
        The preprocessed model.
    """

    args = {**kwargs, **config.get('args', {})}
    model = _process_template(model, **args)

    if rewrap:
        model = rewrap_model(model)

    return model


def save_model(model, output_file=None, output_dir=None, output_prefix='pymzn'):
    """Save a model to file.

    Parameters
    ----------
    model : str
        The minizinc model (i.e. the content of a ``.mzn`` file).
    output_file : str
        The path to the output file. If this parameter is ``None`` (default), a
        temporary file is created with the given model in the specified output
        directory, using the specified prefix.
    output_dir : str
        The directory where to create the file in case ``output_file`` is None.
        Default is ``None``, which creates a file in the system temporary directory.
    output_prefix : str
        The prefix for the output file if created. Default is ``'pymzn'``.

    Returns
    -------
    str
        The path to the newly created ``.mzn`` file.
    """
    if output_file:
        mzn_file = output_file
        output_file = open(output_file, 'w+', buffering=1)
    else:
        output_prefix += '_'
        output_file = NamedTemporaryFile(
            dir=output_dir, prefix=output_prefix, suffix='.mzn', delete=False,
            mode='w+', buffering=1
        )
        mzn_file = output_file.name

    output_file.write(model)
    output_file.close()

    logger.info('Generated file: {}'.format(mzn_file))
    return mzn_file


def _cleanup(files):
    with contextlib.suppress(FileNotFoundError):
        for _file in files:
            if _file:
                os.remove(_file)
                logger.info('Deleted file: {}'.format(_file))


def _prepare_data(mzn_file, data, keep_data=False, declare_enums=True):
    if not data:
        return None, None

    if isinstance(data, dict):
        data = dict2dzn(data, declare_enums=declare_enums)
    elif isinstance(data, str):
        data = [data]
    elif not isinstance(data, list):
        raise TypeError('The additional data provided is not valid.')

    if keep_data or sum(map(len, data)) >= int(config.dzn_width):
        mzn_base, __ = os.path.splitext(mzn_file)
        data_file = mzn_base + '_data.dzn'
        with open(data_file, 'w') as f:
            f.write('\n'.join(data))
        logger.debug('Generated file: {}'.format(data_file))
        data = None
    else:
        data = ' '.join(data)
        data_file = None
    return data, data_file


def _flattening_args(
    mzn, *dzn_files, data=None, stdlib_dir=None, globals_dir=None,
    output_mode='dict', include=None, no_ozn=False, output_base=None,
    allow_multiple_assignments=False
):
    args = []

    if stdlib_dir:
        args += ['--stdlib_dir', stdlib_dir]
    if globals_dir:
        args += ['-G', globals_dir]
    if output_mode and output_mode in ['dzn', 'json', 'item']:
        args += ['--output-mode', output_mode]
    if no_ozn:
        args.append('--no-output-ozn')
    if output_base:
        args += ['--output-base', output_base]
    if allow_multiple_assignments:
        args.append('--allow-multiple-assignments')

    if include:
        if isinstance(include, str):
            include = [include]
        elif not isinstance(include, list):
            raise TypeError('The include path is not valid.')
    else:
        include = []

    include += config.get('include', [])
    for path in include:
        args += ['-I', path]

    if data:
        args += ['-D', data]

    if mzn.endswith('.mzn'):
        args += [mzn] + list(dzn_files)
    else:
        args += list(dzn_files) + ['-']

    return args


def check_instance(
    mzn, *dzn_files, data=None, include=None, stdlib_dir=None, globals_dir=None,
    allow_multiple_assignments=False
):
    """Perform instance checking on a model + data.

    This function calls the command ``minizinc --instance-check-only`` to check
    for consistency of the given model + data.

    Parameters
    ----------
    mzn : str
        The minizinc model. This can be either the path to the ``.mzn`` file or
        the content of the model itself.
    *dzn_files
        A list of paths to dzn files to attach to the minizinc execution,
        provided as positional arguments; by default no data file is attached.
    data : dict
        Additional data as a list of strings containing dzn variables
        assignments.
    include : str or list
        One or more additional paths to search for included ``.mzn`` files.
    stdlib_dir : str
        The path to the MiniZinc standard library. Provide it only if it is
        different from the default one.
    globals_dir : str
        The path to the MiniZinc globals directory. Provide it only if it is
        different from the default one.
    allow_multiple_assignments : bool
        Whether to allow multiple assignments of variables. Sometimes is
        convenient to simply let the data file override the value already
        assigned in the minizinc file. Default is ``False``.

    Raises
    ------
        ``MiniZincError`` if instance checking fails.
    """

    args = ['--instance-check-only']
    args += _flattening_args(
        mzn, *dzn_files, data=data, include=include, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir,
        allow_multiple_assignments=allow_multiple_assignments
    )

    input = mzn if args[-1] == '-' else None
    proc = _run_minizinc_proc(*args, input=input)

    if proc.stderr_data:
        raise MiniZincError(
            mzn if input is None else '\n' + mzn + '\n', args, proc.stderr_data
        )

    logger.info('Instance checking passed.')


def check_model(
    mzn, *, include=None, stdlib_dir=None, globals_dir=None
):
    """Perform model checking on a given model.

    This function calls the command ``minizinc --model-check-only`` to check
    for consistency of the given model.

    Parameters
    ----------
    mzn : str
        The minizinc model. This can be either the path to the ``.mzn`` file or
        the content of the model itself.
    include : str or list
        One or more additional paths to search for included ``.mzn`` files.
    stdlib_dir : str
        The path to the MiniZinc standard library. Provide it only if it is
        different from the default one.
    globals_dir : str
        The path to the MiniZinc globals directory. Provide it only if it is
        different from the default one.

    Raises
    ------
        ``MiniZincError`` if model checking fails.
    """

    args = ['--model-check-only']
    args += _flattening_args(
        mzn, include=include, stdlib_dir=stdlib_dir, globals_dir=globals_dir
    )

    input = mzn if args[-1] == '-' else None
    proc = _run_minizinc_proc(*args, input=input)

    if proc.stderr_data:
        raise MiniZincError(
            mzn if input is None else '\n' + mzn + '\n', args, proc.stderr_data
        )

    logger.info('Model checking passed.')


def _minizinc_preliminaries(
    mzn, *dzn_files, args=None, data=None, include=None, stdlib_dir=None,
    globals_dir=None, output_vars=None, keep=False, output_base=None,
    output_mode='dict', declare_enums=True, allow_multiple_assignments=False
):
    logger.info('Starting preliminaries, received arguments: {}'.format({
        'include': include, 'stdlib_dir': stdlib_dir,
        'globals_dir': globals_dir, 'output_vars': output_vars, 'keep': keep,
        'output_base': output_base, 'output_mode': output_mode,
        'declare_enums': declare_enums,
        'allow_multiple_assignments': allow_multiple_assignments
    }))

    check_version()

    if mzn and isinstance(mzn, str):
        if mzn.endswith('mzn'):
            if os.path.isfile(mzn):
                mzn_file = mzn
                with open(mzn) as f:
                    model = f.read()
            else:
                raise ValueError('The file does not exist.')
        else:
            mzn_file = None
            model = mzn
    else:
        raise TypeError(
            'The mzn variable must be either the path to or the '
            'content of a MiniZinc model file.'
        )

    keep = config.get('keep', keep)

    model = preprocess_model(model, rewrap=keep, **(args or {}))

    check_model(
        model, include=include, stdlib_dir=stdlib_dir, globals_dir=globals_dir
    )

    types = _var_types(
        model, allow_multiple_assignments=allow_multiple_assignments
    )

    if output_mode == 'dict':
        model = _process_output_vars(
            model, types, output_vars,
            allow_multiple_assignments=allow_multiple_assignments
        )

    output_dir = None
    output_prefix = 'pymzn'
    if keep:
        if output_base:
            output_dir, output_prefix = os.path.split(output_base)
        else:
            mzn_dir = os.getcwd()
            if mzn_file:
                mzn_dir, mzn_name = os.path.split(mzn_file)
                output_prefix, _ = os.path.splitext(mzn_name)
            output_dir = mzn_dir
        logger.info('Keeping files in directory: {}'.format(output_dir))

    mzn_file = save_model(
        model, output_dir=output_dir, output_prefix=output_prefix
    )

    dzn_files = list(dzn_files)
    data, data_file = _prepare_data(
        mzn_file, data, keep, declare_enums=declare_enums
    )
    if data_file:
        dzn_files.append(data_file)

    check_instance(
        model, *dzn_files, data=data, include=include, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir,
        allow_multiple_assignments=allow_multiple_assignments
    )

    if output_mode == 'dict':
        _output_mode = 'item'
    else:
        _output_mode = output_mode

    logger.info('Derived output_mode: {}'.format(_output_mode))

    return mzn_file, dzn_files, data_file, data, keep, _output_mode, types


def minizinc(
    mzn, *dzn_files, args=None, data=None, include=None, stdlib_dir=None,
    globals_dir=None, declare_enums=True, allow_multiple_assignments=False,
    keep=False, output_vars=None, output_base=None, output_mode='dict',
    solver=None, timeout=None, two_pass=None, pre_passes=None,
    output_objective=False, non_unique=False, all_solutions=False,
    num_solutions=None, free_search=False, parallel=None, seed=None,
    rebase_arrays=True, keep_solutions=True, return_enums=False, **kwargs
):
    """Implements the workflow for solving a CSP problem encoded with MiniZinc.

    Parameters
    ----------
    mzn : str
        The minizinc model. This can be either the path to the ``.mzn`` file or
        the content of the model itself.
    *dzn_files
        A list of paths to dzn files to attach to the minizinc execution,
        provided as positional arguments; by default no data file is attached.
    args : dict
        Arguments for the template engine.
    data : dict
        Additional data as a dictionary of variables assignments to supply to
        the minizinc executable. The dictionary is automatically converted to
        dzn format by the ``pymzn.dict2dzn`` function.
    include : str or list
        One or more additional paths to search for included ``.mzn`` files.
    stdlib_dir : str
        The path to the MiniZinc standard library. Provide it only if it is
        different from the default one.
    globals_dir : str
        The path to the MiniZinc globals directory. Provide it only if it is
        different from the default one.
    declare_enums : bool
        Whether to declare enum types when converting inline data into dzn
        format. If the enum types are declared elsewhere this option should be
        False. Default is ``True``.
    allow_multiple_assignments : bool
        Whether to allow multiple assignments of variables. Sometimes is
        convenient to simply let the data file override the value already
        assigned in the minizinc file. Default is ``False``.
    keep : bool
        Whether to keep the generated ``.mzn``, ``.dzn``, ``.fzn`` and ``.ozn``
        files or not. If False, the generated files are created as temporary
        files which will be deleted right after the problem is solved. Though
        files generated by PyMzn are not intended to be kept, this property can
        be used for debugging purpose. Note that in case of error the files are
        not deleted even if this parameter is ``False``. Default is ``False``.
    output_vars : list of str
        A list of output variables. These variables will be the ones included in
        the output dictionary. Only available if ``ouptut_mode='dict'``.
    output_base : str
        Output directory for the files generated by PyMzn. The default
        (``None``) is the temporary directory of your OS (if ``keep=False``) or
        the current working directory (if ``keep=True``).
    output_mode : {'dict', 'item', 'dzn', 'json', 'raw'}
        The desired output format. The default is ``'dict'`` which returns a
        stream of solutions decoded as python dictionaries. The ``'item'``
        format outputs a stream of strings as returned by the ``solns2out``
        tool, formatted according to the output statement of the MiniZinc model.
        The ``'dzn'`` and ``'json'`` formats output a stream of strings
        formatted in dzn of json respectively. The ``'raw'`` format, instead
        returns the whole solution stream, without parsing.
    solver : Solver
        The ``Solver`` instance to use. The default solver is ``gecode``.
    timeout : int
        The timeout in seconds for the flattening + solving process.
    two_pass : bool or int
        If ``two_pass`` is True, then it is equivalent to the ``--two-pass``
        option for the ``minizinc`` executable. If ``two_pass`` is an integer
        ``<n>``, instead, it is equivalent to the ``-O<n>`` option for the
        ``minizinc`` executable.
    pre_passes : int
        Equivalent to the ``--pre-passes`` option for the ``minizinc``
        executable.
    output_objective : bool
        Equivalent to the ``--output-objective`` option for the ``minizinc``
        executable. Adds a field ``_objective`` to all solutions.
    non_unique : bool
        Equivalent to the ``--non-unique`` option for the ``minizinc``
        executable.
    all_solutions : bool
        Whether all the solutions must be returned. This option might not work
        if the solver does not support it. Default is ``False``.
    num_solutions : int
        The upper bound on the number of solutions to be returned. This option
        might not work if the solver does not support it. Default is ``1``.
    free_search : bool
        If ``True``, instruct the solver to perform free search.
    parallel : int
        The number of parallel threads the solver can utilize for the solving.
    seed : int
        The random number generator seed to pass to the solver.
    rebase_arrays : bool
        Whether to "rebase" parsed arrays (see the `Dzn files
        <http://paolodragone.com/pymzn/reference/dzn>`__ section). Default is
        True.
    keep_solutions : bool
        Whether to store the solutions in memory after solving is done. If
        ``keep_solutions`` is ``False``, the returned solution stream can only
        be iterated once and cannot be addressed as a list.
    return_enums : bool
        Wheter to return enum types along with the variable assignments in the
        solutions. Only used if ``output_mode='dict'``. Default is ``False``.
    **kwargs
        Additional arguments to pass to the solver, provided as additional
        keyword arguments to this function. Check the solver documentation for
        the available arguments.

    Returns
    -------
    Solutions or str
        If ``output_mode`` is not ``'raw'``, returns a list-like object
        containing the solutions found by the solver. The format of the solution
        depends on the specified ``output_mode``. If ``keep_solutions=False``,
        the returned object cannot be addressed as a list and can only be
        iterated once. If ``output_mode='raw'``, the function returns the whole
        solution stream as a single string.
    """

    mzn_file, dzn_files, data_file, data, keep, _output_mode, types = \
        _minizinc_preliminaries(
            mzn, *dzn_files, args=args, data=data, include=include,
            stdlib_dir=stdlib_dir, globals_dir=globals_dir,
            output_vars=output_vars, keep=keep, output_base=output_base,
            output_mode=output_mode, declare_enums=declare_enums,
            allow_multiple_assignments=allow_multiple_assignments
        )

    if not solver:
        solver = config.get('solver', gecode)

    solver_args = {**kwargs, **config.get('solver_args', {})}

    proc = solve(
        solver, mzn_file, *dzn_files, data=data, include=include,
        stdlib_dir=stdlib_dir, globals_dir=globals_dir,
        output_mode=_output_mode, timeout=timeout, two_pass=two_pass,
        pre_passes=pre_passes, output_objective=output_objective,
        non_unique=non_unique, all_solutions=all_solutions,
        num_solutions=num_solutions, free_search=free_search, parallel=parallel,
        seed=seed, allow_multiple_assignments=allow_multiple_assignments,
        **solver_args
    )

    if not keep:
        _cleanup([mzn_file, data_file])

    if output_mode == 'raw':
        logger.info('Returning raw output from the solver.')
        return proc.stdout_data

    logger.info('Creating solution parser with arguments: {}'.format({
        'output_mode': output_mode, 'rebase_arrays': rebase_arrays,
        'types': types, 'keep_solutions': keep_solutions,
        'return_enums': return_enums
    }))

    parser = SolutionParser(
        solver, output_mode=output_mode, rebase_arrays=rebase_arrays,
        types=types, keep_solutions=keep_solutions, return_enums=return_enums
    )
    solns = parser.parse(proc)
    return solns


def _solve_args(
    solver, timeout=None, two_pass=None, pre_passes=None,
    output_objective=False, non_unique=False, all_solutions=False,
    num_solutions=None, free_search=False, parallel=None, seed=None, **kwargs
):
    args = []
    if timeout:
        args += ['--time-limit', str(timeout * 1000)] # minizinc takes milliseconds

    if two_pass:
        if isinstance(two_pass, bool):
            args.append('--two-pass')
        elif isinstance(two_pass, int):
            args.append('-O{}'.format(two_pass))

    if pre_passes:
        args += ['--pre-passes', str(pre_passes)]

    if output_objective:
        args.append('--output-objective')

    if non_unique:
        args.append('--non-unique')

    args += ['--solver', solver.solver_id]
    args += solver.args(
        all_solutions=all_solutions, num_solutions=num_solutions,
        free_search=free_search, parallel=parallel, seed=seed, **kwargs
    )

    return args


def solve(
    solver, mzn, *dzn_files, data=None, include=None, stdlib_dir=None,
    globals_dir=None, allow_multiple_assignments=False, output_mode='item',
    timeout=None, two_pass=None, pre_passes=None, output_objective=False,
    non_unique=False, all_solutions=False, num_solutions=None,
    free_search=False, parallel=None, seed=None, **kwargs
):
    """Flatten and solve a MiniZinc program.

    Parameters
    ----------
    solver : Solver
        The ``Solver`` instance to use.
    mzn : str
        The path to the minizinc model file.
    *dzn_files
        A list of paths to dzn files to attach to the minizinc execution,
        provided as positional arguments; by default no data file is attached.
    data : list of str
        Additional data as a list of strings containing dzn variables
        assignments.
    include : str or list
        One or more additional paths to search for included ``.mzn`` files.
    stdlib_dir : str
        The path to the MiniZinc standard library. Provide it only if it is
        different from the default one.
    globals_dir : str
        The path to the MiniZinc globals directory. Provide it only if it is
        different from the default one.
    allow_multiple_assignments : bool
        Whether to allow multiple assignments of variables. Sometimes is
        convenient to simply let the data file override the value already
        assigned in the minizinc file. Default is ``False``.
    output_mode : {'item', 'dzn', 'json'}
        The desired output format. The default is ``'item'`` which outputs a
        stream of strings as returned by the ``solns2out`` tool, formatted
        according to the output statement of the MiniZinc model. The ``'dzn'``
        and ``'json'`` formats output a stream of strings formatted in dzn and
        json respectively.
    timeout : int
        The timeout in seconds for the flattening + solving process.
    two_pass : bool or int
        If ``two_pass`` is True, then it is equivalent to the ``--two-pass``
        option for the ``minizinc`` executable. If ``two_pass`` is an integer
        ``<n>``, instead, it is equivalent to the ``-O<n>`` option for the
        ``minizinc`` executable.
    pre_passes : int
        Equivalent to the ``--pre-passes`` option for the ``minizinc``
        executable.
    output_objective : bool
        Equivalent to the ``--output-objective`` option for the ``minizinc``
        executable. Adds a field ``_objective`` to all solutions.
    non_unique : bool
        Equivalent to the ``--non-unique`` option for the ``minizinc``
        executable.
    all_solutions : bool
        Whether all the solutions must be returned. This option might not work
        if the solver does not support it. Default is ``False``.
    num_solutions : int
        The upper bound on the number of solutions to be returned. This option
        might not work if the solver does not support it. Default is ``1``.
    free_search : bool
        If True, instruct the solver to perform free search.
    parallel : int
        The number of parallel threads the solver can utilize for the solving.
    seed : int
        The random number generator seed to pass to the solver.
    **kwargs
        Additional arguments to pass to the solver, provided as additional
        keyword arguments to this function. Check the solver documentation for
        the available arguments.

    Returns
    -------
        Object wrapping the executed process.
    """

    args = _solve_args(
        solver, timeout=timeout, two_pass=two_pass, pre_passes=pre_passes,
        output_objective=output_objective, non_unique=non_unique,
        all_solutions=all_solutions, num_solutions=num_solutions,
        free_search=free_search, parallel=parallel, seed=seed, **kwargs
    )

    args += _flattening_args(
        mzn, *dzn_files, data=data, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir, output_mode=output_mode, include=include,
        allow_multiple_assignments=allow_multiple_assignments
    )

    input = mzn if args[-1] == '-' else None

    t0 = _time()

    try:
        proc = _run_minizinc_proc(*args, input=input)
    except RuntimeError as err:
        raise MiniZincError(mzn_file, args) from err

    solve_time = _time() - t0
    logger.info('Solving completed in {:>3.2f} sec'.format(solve_time))

    return proc


def mzn2fzn(
    mzn, *dzn_files, args=None, data=None, include=None, stdlib_dir=None,
    globals_dir=None, declare_enums=True, allow_multiple_assignments=False,
    keep=False, output_vars=None, output_base=None, output_mode='item',
    no_ozn=False
):
    """Flatten a MiniZinc model into a FlatZinc one.

    This function is equivalent to the command ``minizinc --compile``.

    Parameters
    ----------
    mzn : str
        The minizinc model. This can be either the path to the ``.mzn`` file or
        the content of the model itself.
    *dzn_files
        A list of paths to dzn files to attach to the minizinc execution,
        provided as positional arguments; by default no data file is attached.
    args : dict
        Arguments for the template engine.
    data : dict
        Additional data as a dictionary of variables assignments to supply to
        the minizinc executable. The dictionary is automatically converted to
        dzn format by the ``pymzn.dict2dzn`` function.
    include : str or list
        One or more additional paths to search for included ``.mzn`` files.
    stdlib_dir : str
        The path to the MiniZinc standard library. Provide it only if it is
        different from the default one.
    globals_dir : str
        The path to the MiniZinc globals directory. Provide it only if it is
        different from the default one.
    declare_enums : bool
        Whether to declare enum types when converting inline data into dzn
        format. If the enum types are declared elsewhere this option should be
        False. Default is ``True``.
    allow_multiple_assignments : bool
        Whether to allow multiple assignments of variables. Sometimes is
        convenient to simply let the data file override the value already
        assigned in the minizinc file. Default is ``False``.
    keep : bool
        Whether to keep the generated ``.mzn``, ``.dzn``, ``.fzn`` and ``.ozn``
        files or not. If False, the generated files are created as temporary
        files which will be deleted right after the problem is solved. Though
        files generated by PyMzn are not intended to be kept, this property can
        be used for debugging purpose. Note that in case of error the files are
        not deleted even if this parameter is ``False``. Default is ``False``.
    output_vars : list of str
        A list of output variables. These variables will be the ones included in
        the output dictionary. Only available if ``ouptut_mode='dict'``.
    output_base : str
        Output directory for the files generated by PyMzn. The default
        (``None``) is the temporary directory of your OS (if ``keep=False``) or
        the current working directory (if ``keep=True``).
    output_mode : {'dict', 'item', 'dzn', 'json', 'raw'}
        The desired output format. The default is ``'dict'`` which returns a
        stream of solutions decoded as python dictionaries. The ``'item'``
        format outputs a stream of strings as returned by the ``solns2out``
        tool, formatted according to the output statement of the MiniZinc model.
        The ``'dzn'`` and ``'json'`` formats output a stream of strings
        formatted in dzn and json respectively. The ``'raw'`` format, instead
        returns the whole solution stream, without parsing.
    no_ozn : bool
        If ``True``, the ozn file is not produced, ``False`` otherwise.

    Returns
    -------
    tuple (str, str)
        The paths to the generated fzn and ozn files. If ``no_ozn=True``, the
        second argument is ``None``.
    """

    mzn_file, dzn_files, data_file, data, keep, _output_mode, types = \
        _minizinc_preliminaries(
            mzn, *dzn_files, args=args, data=data, include=include,
            stdlib_dir=stdlib_dir, globals_dir=globals_dir,
            output_vars=output_vars, keep=keep, output_base=output_base,
            output_mode=output_mode, declare_enums=declare_enums,
            allow_multiple_assignments=allow_multiple_assignments
        )

    args = ['--compile']
    args += _flattening_args(
        mzn_file, *dzn_files, data=data, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir, output_mode=output_mode, include=include,
        no_ozn=no_ozn, output_base=output_base,
        allow_multiple_assignments=allow_multiple_assignments
    )

    t0 = _time()
    _run_minizinc(*args)
    flattening_time = _time() - t0
    logger.info('Flattening completed in {:>3.2f} sec'.format(flattening_time))

    if not keep:
        with contextlib.suppress(FileNotFoundError):
            if data_file:
                os.remove(data_file)
                logger.info('Deleted file: {}'.format(data_file))

    if output_base:
        mzn_base = output_base
    else:
        mzn_base = os.path.splitext(mzn_file)[0]

    fzn_file = '.'.join([mzn_base, 'fzn'])
    fzn_file = fzn_file if os.path.isfile(fzn_file) else None
    ozn_file = '.'.join([mzn_base, 'ozn'])
    ozn_file = ozn_file if os.path.isfile(ozn_file) else None

    if fzn_file:
        logger.info('Generated file: {}'.format(fzn_file))
    if ozn_file:
        logger.info('Generated file: {}'.format(ozn_file))

    return fzn_file, ozn_file


def solns2out(stream, ozn_file):
    """Wraps the ``solns2out`` utility, executes it on the solution stream, and
    then returns the output stream.

    Parameters
    ----------
    stream : str
        A solution stream. It may be a solution stream saved by a previous call
        to minizinc.
    ozn_file : str
        The path to the ``.ozn`` file produced by the ``mzn2fzn`` function.

    Returns
    -------
    str
        The output stream of solns2out encoding the solution stream according to
        the provided ozn file.
    """
    return _run_minizinc('--ozn-file', ozn_file, input=stream)


class MiniZincError(RuntimeError):
    """Generic error raised by the PyMzn functions.

    Arguments
    ---------
    mzn_file : str
        The MiniZinc file that generated the error.
    args : list of str
        The command line arguments that generated the error.
    stderr : str
        The standard error printed by the ``minizinc`` executable.
    """

    def __init__(self, mzn_file, args, stderr=None):
        self.mzn_file = mzn_file
        self.args = args
        self.stderr = stderr
        msg = (
            'An error occurred while executing minizinc on file {} '
            'with command line arguments: {}'
        ).format(mzn_file, args)
        if stderr:
            msg += '\n\n' + stderr
        super().__init__(msg)

