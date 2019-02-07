# -*- coding: utf-8 -*-
"""
PyMzn provides functions that mimic and enhance the tools from the libminizinc
library. With these tools, it is possible to compile a MiniZinc model into a
FlatZinc one, solve a given problem and get the output solutions directly into
the python code.

The main function that PyMzn provides is the ``minizinc`` function, which
executes the entire workflow for solving a constranint program encoded in
MiniZinc.  Solving a MiniZinc problem with PyMzn is as simple as::

    import pymzn
    pymzn.minizinc('test.mzn')

The ``minizinc`` function is probably the way to go for most of the problems,
but the ``mzn2fzn`` and ``solns2out`` functions are also included in the public
API to allow for maximum flexibility. The latter two functions are wrappers of
the two homonym MiniZinc tools for, respectively, converting a MiniZinc model
into a FlatZinc one and getting custom output from the solution stream of a
solver.
"""

import os
import re
import json
import contextlib

from time import monotonic as _time
from tempfile import NamedTemporaryFile

from .. import config as config

from ..log import logger
from .solvers import gecode
from .templates import from_string
from .process import run_process
from .output import SolutionParser
from ..dzn import dict2dzn

__all__ = [
    'minizinc_version', 'preprocess_model', 'save_model', 'check_model',
    'minizinc', 'solve', 'mzn2fzn', 'solns2out'
]


def _run_minizinc_proc(*args, input=None):
    args = [config.get('minizinc', 'minizinc')] + list(args)
    logger.debug('Executing minizinc with arguments: {}'.format(args))
    return run_process(*args, input=input)


def _run_minizinc(*args, input=None):
    proc = _run_minizinc_proc(*args, input=input)
    return proc.stdout_data


def _process_template(model, **kwargs):
    return from_string(model, kwargs)


def _var_types(mzn):
    args = ['--model-types-only']
    input = None
    if mzn.endswith('.mzn'):
        args.append(mzn)
    else:
        args.append('-')
        input = mzn.encode()
    json_str = _run_minizinc(*args, input=input)
    return json.loads(json_str)['var_types']['vars']


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

    output = ', '.join(enum_list ++ out_list)
    output_stmt = 'output [{}];'.format(output)
    return output_stmt


def _process_output_vars(model, output_vars=None):
    if output_vars is None:
        return model
    types = _var_types(model)
    output_stmt = _dzn_output_statement(output_vars, types)
    output_stmt_p = re.compile('\s*output\s*\[(.+?)\]\s*(?:;)?\s*')
    return output_stmt_p.sub(output_stmt, model)


def _rewrap(s):
    S = {' ', '\t', '\n', '\r', '\f', '\v'}
    stmts_p = re.compile('(?:^|;)([^;]+)')
    stmts = []
    for stmt in stmts_p.findall(s):
        spaces = 0
        while spaces < len(stmt) and stmt[spaces] in S:
            spaces += 1
        spaces -= stmt[0] == '\n'
        lines = []
        for line in stmt.splitlines():
            start = 0
            while start < len(line) and start < spaces and line[start] in S:
                start += 1
            lines.append(line[start:])
        stmts.append('\n'.join(lines))
    return ';\n'.join(stmts)


def preprocess_model(model, output_vars=None, rewrap=True, **kwargs):

    args = {**kwargs, **config.get('args', {})}
    model = _process_template(model, **args)

    if rewrap:
        model = _rewrap(model)
    else:
        block_comm_p = re.compile('/\*.*\*/', re.DOTALL)
        model = block_comm_p.sub('', model)
        line_comm_p = re.compile('%.*\n')
        model = line_comm_p.sub('', model)

    model = _process_output_vars(model, output_vars)
    return model


def save_model(model, output_file=None, output_dir=None, output_prefix='pymzn'):
    if output_file:
        mzn_file = output_file
        output_file = open(output_file, 'w+', buffering=1)
    else:
        if not output_dir:
            output_dir = config.get('output_dir', None)

        output_prefix += '_'
        output_file = NamedTemporaryFile(
            dir=output_dir, prefix=output_prefix, suffix='.mzn', delete=False,
            mode='w+', buffering=1
        )
        mzn_file = output_file.name

    output_file.write(model)
    output_file.close()

    logger.debug('Generated file {}'.format(mzn_file))
    return mzn_file


def _cleanup(files):
    with contextlib.suppress(FileNotFoundError):
        for _file in files:
            if _file:
                os.remove(_file)
                logger.debug('Deleted file: {}'.format(_file))


def _prepare_data(mzn_file, data, keep_data=False):
    if not data:
        return None, None

    if isinstance(data, dict):
        data = dict2dzn(data)
    elif isinstance(data, str):
        data = [data]
    elif not isinstance(data, list):
        raise TypeError('The additional data provided is not valid.')

    if keep_data or sum(map(len, data)) >= config.get('dzn_width', 70):
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


def minizinc_version():
    vs = _run_minizinc('--version')
    m = re.findall('version ([\d\.]+)', vs)
    return m[0]


def _flattening_args(
    mzn_file, *dzn_files, data=None, keep=False, stdlib_dir=None,
    globals_dir=None, output_mode='dict', include=None, no_ozn=False,
    output_base=None
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
    args += [mzn_file] + list(dzn_files)

    return args


def check_model(
    mzn_file, *dzn_files, data=None, include=None, stdlib_dir=None,
    globals_dir=None
):
    args = _flattening_args(
        mzn_file, *dzn_files, data=data, include=include, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir
    )
    args.append('--instance-check-only')

    proc = _run_minizinc_proc(*args)
    if proc.stderr_data:
        raise MiniZincError(mzn_file, args, proc.stderr_data)


def minizinc(
    mzn, *dzn_files, args=None, data=None, include=None, stdlib_dir=None,
    globals_dir=None, output_vars=None, keep=False, output_dir=None,
    output_mode='dict', solver=None, timeout=None, all_solutions=False,
    num_solutions=None, free_search=False, parallel=None, seed=None, **kwargs
):
    """Implements the workflow to solve a CSP problem encoded with MiniZinc.

    Parameters
    ----------
    mzn : str or MiniZincModel
        The minizinc problem to be solved.  It can be either a string or an
        instance of MiniZincModel.  If it is a string, it can be either the path
        to the mzn file or the content of the model.
    *dzn_files
        A list of paths to dzn files to attach to the mzn2fzn execution,
        provided as positional arguments; by default no data file is attached.
        Data files are meant to be used when there is data that is static across
        several minizinc executions.
    data : dict
        Additional data as a dictionary of variables assignments to supply to
        the mzn2fnz function. The dictionary is then automatically converted to
        dzn format by the pymzn.dzn function. This property is meant to include
        data that dynamically changes across several minizinc executions.
    keep : bool
        Whether to keep the generated mzn, dzn, fzn and ozn files or not. If
        False, the generated files are created as temporary files which will be
        deleted right after the problem is solved. Though pymzn generated files
        are not originally intended to be kept, this property can be used for
        debugging purpose. Notice that in case of error the files are not
        deleted even if this parameter is False.  Default is False.
    include : str or list
        One or more additional paths to search for included mzn files.
    solver : Solver
        An instance of Solver to use to solve the minizinc problem. The default
        is pymzn.gecode.
    output_mode : 'dzn', 'json', 'item', 'dict'
        The desired output format. The default is 'dict' which returns a stream
        of solutions decoded as python dictionaries. The 'item' format outputs a
        stream of strings as returned by the solns2out tool, formatted according
        to the output statement of the MiniZinc model. The 'dzn' and 'json'
        formats output a stream of strings formatted in dzn of json
        respectively.
    output_vars : [str]
        A list of output variables. These variables will be the ones included in
        the output dictionary. Only available if ouptut_mode='dict'.
    output_dir : str
        Output directory for files generated by PyMzn. The default (None) is the
        temporary directory of your OS (if keep=False) or the current working
        directory (if keep=True).
    timeout : int
        Number of seconds after which the solver should stop the computation and
        return the best solution found. This is only available if the solver has
        support for a timeout.
    all_solutions : bool
        Whether all the solutions must be returned. Notice that this can only
        be used if the solver supports returning all solutions. Default is False.
    num_solutions : int
        The upper bound on the number of solutions to be returned. Can only be
        used if the solver supports returning a fixed number of solutions.
        Default is 1.
    args : dict
        Arguments for the template engine.
    **kwargs
        Additional arguments to pass to the solver, provided as additional
        keyword arguments to this function. Check the solver documentation for
        the available arguments.

    Returns
    -------
    Solutions
        Returns a list of solutions as a Solutions instance. The actual content
        of the stream depends on the output_mode chosen.
    """
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

    model = preprocess_model(
        model, output_vars=output_vars, rewrap=keep, **(args or {})
    )

    output_prefix = 'pymzn'
    if keep:
        mzn_dir = os.getcwd()
        if mzn_file:
            mzn_dir, mzn_name = os.path.split(mzn_file)
            output_prefix, _ = os.path.splitext(mzn_name)
        output_dir = output_dir or mzn_dir

    mzn_file = save_model(
        model, output_dir=output_dir, output_prefix=output_prefix
    )

    dzn_files = list(dzn_files)
    data, data_file = _prepare_data(mzn_file, data, keep)
    if data_file:
        dzn_files.append(data_file)

    check_model(
        mzn_file, *dzn_files, data=data, include=include, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir
    )

    if output_mode == 'dict':
        if output_vars:
            _output_mode = 'item'
        else:
            _output_mode = 'dzn'
    else:
        _output_mode = output_mode

    if not solver:
        solver = config.get('solver', gecode)

    all_solutions = config.get('all_solutions', all_solutions)
    num_solutions = config.get('num_solutions', num_solutions)
    timeout = config.get('timeout', timeout)

    solver_args = {**kwargs, **config.get('solver_args', {})}

    proc = solve(
        solver, mzn_file, *dzn_files, data=data, include=include,
        stdlib_dir=stdlib_dir, globals_dir=globals_dir, keep=keep,
        output_mode=_output_mode, timeout=timeout, all_solutions=all_solutions,
        num_solutions=num_solutions, free_search=free_search, parallel=parallel,
        seed=seed, **solver_args
    )

    parser = SolutionParser(solver, output_mode=output_mode)
    solns = parser.parse(proc)

    if not keep:
        _cleanup([mzn_file, data_file])

    return solns


def solve(
    solver, mzn_file, *dzn_files, data=None, include=None, stdlib_dir=None,
    globals_dir=None, keep=False, output_mode='dict', timeout=None,
    all_solutions=False, num_solutions=None, free_search=False, parallel=None,
    seed=None, **kwargs
):
    args = _flattening_args(
        mzn_file, *dzn_files, data=data, keep=keep, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir, output_mode=output_mode, include=include
    )

    if timeout:
        args += ['--time-limit', timeout * 1000] # minizinc takes milliseconds

    args += ['--solver', solver.solver_id]
    args += solver.args(
        all_solutions=all_solutions, num_solutions=num_solutions,
        free_search=free_search, parallel=parallel, seed=seed, **kwargs
    )

    t0 = _time()

    try:
        proc = _run_minizinc_proc(*args)
    except RuntimeError as err:
        raise MiniZincError(mzn_file, args) from err

    solve_time = _time() - t0
    logger.debug('Solving completed in {:>3.2f} sec'.format(solve_time))

    return proc


def mzn2fzn(
    mzn_file, *dzn_files, data=None, keep_data=False, stdlib_dir=None,
    globals_dir=None, output_mode='dict', include=None, no_ozn=False,
    output_base=None
):
    """Flatten a MiniZinc model into a FlatZinc one. It executes the mzn2fzn
    utility from libminizinc to produce a fzn and ozn files from a mzn one.

    Parameters
    ----------
    mzn_file : str
        The path to the minizinc problem file.
    *dzn_files
        A list of paths to dzn files to attach to the mzn2fzn execution,
        provided as positional arguments; by default no data file is attached.
    data : dict
        Additional data as a dictionary of variables assignments to supply to
        the mzn2fnz function. The dictionary is then automatically converted to
        dzn format by the ``pymzn.dict2dzn`` function. Notice that if the data
        provided is too large, a temporary dzn file will be produced.
    keep_data : bool
        Whether to write the inline data into a dzn file and keep it.
        Default is False.
    globals_dir : str
        The path to the directory for global included files.
    include : str or list
        One or more additional paths to search for included mzn files when
        running ``mzn2fzn``.
    output_mode : 'dzn', 'json', 'item'
        The desired output format. The default is 'item' which outputs a
        stream of strings as returned by the solns2out tool, formatted according
        to the output statement of the MiniZinc model. The 'dzn' and 'json'
        formats output a stream of strings formatted in dzn of json
        respectively.
    no_ozn : bool
        If True, the ozn file is not produced, False otherwise.

    Returns
    -------
    tuple (str, str)
        The paths to the generated fzn and ozn files. If ``no_ozn=True``, the
        second argument is None.
    """

    dzn_files = list(dzn_files)
    data, data_file = _prepare_data(mzn_file, data, keep_data)
    if data_file:
        dzn_files.append(data_file)

    check_model(
        mzn_file, *dzn_files, data=data, include=include, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir
    )

    args = _flattening_args(
        mzn_file, *dzn_files, data=data, keep=keep_data, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir, output_mode=output_mode, include=include,
        no_ozn=no_ozn, output_base=output_base
    )

    args.append('--compile')

    t0 = _time()
    _run_minizinc(*args)
    flattening_time = _time() - t0
    logger.debug('Flattening completed in {:>3.2f} sec'.format(flattening_time))

    if not keep_data:
        with contextlib.suppress(FileNotFoundError):
            if data_file:
                os.remove(data_file)
                logger.debug('Deleted file: {}'.format(data_file))

    if output_base:
        mzn_base = output_base
    else:
        mzn_base = os.path.splitext(mzn_file)[0]

    fzn_file = '.'.join([mzn_base, 'fzn'])
    fzn_file = fzn_file if os.path.isfile(fzn_file) else None
    ozn_file = '.'.join([mzn_base, 'ozn'])
    ozn_file = ozn_file if os.path.isfile(ozn_file) else None

    if fzn_file:
        logger.debug('Generated file: {}'.format(fzn_file))
    if ozn_file:
        logger.debug('Generated file: {}'.format(ozn_file))

    return fzn_file, ozn_file


def solns2out(stream, ozn_file):
    """Wraps the solns2out utility, executes it on the solution stream, and
    then returns the output stream.

    Parameters
    ----------
    stream : str
        A solution stream. It may be a solution stream saved by a previous call
        to minizinc.
    ozn_file : str
        The ozn file path produced by the mzn2fzn function.

    Returns
    -------
    str
        The output stream of solns2out encoding the solution stream according to
        the provided ozn file.
    """
    return _run_minizinc('--ozn-file', ozn_file, input=stream)


class MiniZincError(RuntimeError):

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

