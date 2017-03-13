# -*- coding: utf-8 -*-
"""
PyMzn provides functions that mimic and enhance the tools from the libminizinc
library. With these tools, it is possible to compile a MiniZinc model into
FlatZinc, solve a given problem and get the output solutions directly into the
python code.

The main function that PyMzn provides is the ``minizinc`` function, which
executes the entire workflow for solving a CSP problem encoded in MiniZinc.
Solving a MiniZinc problem with PyMzn is as simple as:::

    import pymzn
    pymzn.minizinc('test.mzn')

The ``minizinc`` function is probably the way to go for most of the problems,
but the ``mzn2fzn`` and ``solns2out`` functions are in the public API to allow
for maximum flexibility. The latter two functions are wrappers of the two
homonym MiniZinc tools for, respectively, converting a MiniZinc model into a
FlatZinc one and getting custom output from the solution stream of a solver.
"""

import os
import itertools
import contextlib

from subprocess import CalledProcessError
from tempfile import NamedTemporaryFile

import pymzn.config as config

from pymzn.bin import run
from . import _solvers
from ._solvers import gecode
from ._model import MiniZincModel
from pymzn._utils import get_logger
from pymzn._dzn import dzn_eval, dzn


def minizinc(mzn, *dzn_files, data=None, keep=False, output_base=None,
             globals_dir=None, stdlib_dir=None, path=None, eval_output=True,
             output_vars=None, solver=gecode, check_complete=False,
             all_solutions=False, parse_output=True, **solver_args):
    """Implements the workflow to solve a CSP problem encoded with MiniZinc.

    It first calls mzn2fzn to compile the fzn and ozn files, then it calls the
    provided solver and in the end it calls the solns2out utility on the
    output of the solver.

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
    output_base : str
        If ``keep=True``, this parameter is used as the base name for the output
        mzn, dzn, fzn and ozn files (extension are attached automatically). This
        name should include the parent directories if different from the working
        one.  Parent directories are not created automatically so they are
        required to exist. If None is provided (default) the name of the input
        file is used. If the mzn input was a content string, then the default
        name 'pymzn' and the working directory are used.
    globals_dir : str
        The name of the directory where to search for global included files in
        the standard library; by default the solver specific global library is
        used.
    stdlib_dir : str
        The name of the directory containing the standard library of minizinc.
        When None (default) the MiniZinc default is used.
    path : str or list
        One or more additional paths to search for included mzn files when
        running ``mzn2fzn``.
    eval_output : bool
        Whether to evaluate the output of the solver or solns2out function into
        Python objects with the ``pymzn.dzn_eval`` function. If the output is
        not evaluated, then a list of strings containing the solutions is
        returned. This is useful when a custom output statement is given in the
        mzn file. The default value is True. When this argument
    output_vars : list of str
        The list of output variables. If not provided, the default list is the
        list of free variables in the model, i.e. those variables that are
        declared but not defined in the model.  This argument is only used when
        ``eval_output`` is True.
    solver : Solver
        An instance of Solver to use to solve the minizinc problem. The default
        is pymzn.gecode.
    check_complete : bool
        If True, a boolean value is returned, in addition to
        the solutions of the problem, indicating the completion status of the
        problem. The returned boolean is True when the solver completed its work
        and, in case ``all_solutions=True``, returned all the solutions; it is
        False when the solver did not complete its work because e.g. was
        interrupted by a timeout.
    all_solutions : bool
        Whether all the solutions must be returned. Notice that this is only
        used if the solver supports returning all solutions, otherwise it is
        ignored. Default is False.
    **solver_args
        Additional arguments to pass to the solver, provided as additional
        keyword arguments to this function check the solver documentation for
        the available arguments.

    Returns
    -------
    list or tuple
        Returns a list of solutions. If eval_output is True, the solutions are
        returned as dictionaries of variable assignments, otherwise they are
        solution strings as returned from the solns2out function. If
        ``check_complete=True`` the result is a tuple containing the solution
        list as first argument and a boolean value indicating the completion
        status of the problem as second argument.
    """
    log = get_logger(__name__)

    if isinstance(mzn, MiniZincModel):
        mzn_model = mzn
    else:
        mzn_model = MiniZincModel(mzn)

    if eval_output and parse_output:
        mzn_model.dzn_output_stmt(output_vars)

    if not solver:
        solver = gecode
    elif isinstance(solver, str):
        solver = getattr(_solvers, solver)

    _globals_dir = globals_dir or solver.globals_dir

    output_dir = None
    output_prefix = 'pymzn'
    if keep:
        if output_base:
            output_dir, output_prefix = os.path.split(output_base)
        elif mzn_model.mzn_file:
            output_dir, mzn_name = os.path.split(mzn_model.mzn_file)
            output_prefix, mzn_ext = os.path.split(mzn_name)
        else:
            output_dir = os.getcwd()
    output_prefix += '_'
    output_file = NamedTemporaryFile(dir=output_dir, prefix=output_prefix,
                                     suffix='.mzn', delete=False, mode='w+',
                                     buffering=1)
    mzn_model.compile(output_file)
    mzn_file = output_file.name

    fzn_file, ozn_file = mzn2fzn(mzn_file, *dzn_files, data=data,
                                 keep_data=keep, path=path,
                                 globals_dir=_globals_dir,
                                 stdlib_dir=stdlib_dir)

    if not solver.support_all and all_solutions:
        log.warning('Solver does not support returning all solutions.')

    solver_check_complete = not solver.support_ozn and check_complete

    out = solver.solve(fzn_file, check_complete=solver_check_complete,
                       all_solutions=all_solutions, **solver_args)

    if solver_check_complete:
        out, complete = out

    if solver.support_ozn:
        try:
            if check_complete:
                solns, complete = solns2out(out, ozn_file, check_complete=True,
                                            parse_output=parse_output)
            else:
                solns = solns2out(out, ozn_file, parse_output=parse_output)
        except (MiniZincUnsatisfiableError, MiniZincUnknownError,
                MiniZincUnboundedError) as err:
            err.mzn_file = mzn_file
            raise err
    else:
        solns = out

    if eval_output:
        solns = list(map(dzn_eval, solns))

    if not keep:
        with contextlib.suppress(FileNotFoundError):
            if mzn_file:
                os.remove(mzn_file)
                log.debug('Deleting file: {}', mzn_file)
            if fzn_file:
                os.remove(fzn_file)
                log.debug('Deleting file: {}', fzn_file)
            if ozn_file:
                os.remove(ozn_file)
                log.debug('Deleting file: {}', ozn_file)

    if check_complete:
        return solns, complete
    return solns


def mzn2fzn(mzn_file, *dzn_files, data=None, keep_data=False, globals_dir=None,
            stdlib_dir=None, path=None, no_ozn=False):
    """Flatten a MiniZinc model into a FlatZinc one. It executes the mzn2fzn
    utility from libminizinc to produce a fzn and ozn files from a mzn one.

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
    keep_data : bool
        Whether to write the dzn inline data provided in the ``data`` parameter
        into a file and keep it. Default is False.
    globals_dir : str
        The name of the directory where to search for global included files in
        the standard library; by default the solver specific global library is
        used.
    stdlib_dir : str
        The name of the directory containing the standard library of minizinc.
        When None (default) the MiniZinc default is used.
    path : str or list
        One or more additional paths to search for included mzn files when
        running ``mzn2fzn``.
    no_ozn : bool
        If True, the ozn file is not produced, False otherwise.

    Returns
    -------
    tuple (str, str)
        The paths to the generated fzn and ozn files. If ``no_ozn=True``, the
        second argument is None.
    """
    log = get_logger(__name__)

    args = [config.get('mzn2fzn', 'mzn2fzn')]
    if stdlib_dir:
        args.append('--stdlib-dir')
        args.append(stdlib_dir)
    if globals_dir:
        args.append('-G')
        args.append(globals_dir)
    if no_ozn:
        args.append('--no-output-ozn')
    if path:
        if isinstance(path, str):
            path = [path]
        elif not isinstance(path, list):
            raise TypeError('The path provided is not valid.')
        for p in path:
            args.append('-I')
            args.append(p)

    dzn_files = list(dzn_files)
    data_file = None
    if data:
        if isinstance(data, dict):
            data = dzn(data)
        elif isinstance(data, str):
            data = [data]
        elif not isinstance(data, list):
            raise TypeError('The additional data provided is not valid.')

        if keep_data or sum(map(len, data)) >= config.get('dzn_width', 70):
            mzn_base, __ = os.path.splitext(mzn_file)
            data_file = mzn_base + '_data.dzn'
            with open(data_file, 'w') as f:
                f.write('\n'.join(data))
            dzn_files.append(data_file)
            log.debug('Generated file: {}', data_file)
        else:
            data = ' '.join(data)
            args.append('-D')
            args.append(data)

    args += [mzn_file] + dzn_files

    try:
        run(args)
    except CalledProcessError as err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr) from err

    if not keep_data:
        with contextlib.suppress(FileNotFoundError):
            if data_file:
                os.remove(data_file)
                log.debug('Deleting file: {}', data_file)

    mzn_base = os.path.splitext(mzn_file)[0]
    fzn_file = '.'.join([mzn_base, 'fzn'])
    fzn_file = fzn_file if os.path.isfile(fzn_file) else None
    ozn_file = '.'.join([mzn_base, 'ozn'])
    ozn_file = ozn_file if os.path.isfile(ozn_file) else None

    if fzn_file:
        log.debug('Generated file: {}', fzn_file)
    if ozn_file:
        log.debug('Generated file: {}', ozn_file)

    return fzn_file, ozn_file


def solns2out(soln_stream, ozn_file, check_complete=False, parse_output=True):
    """Wraps the solns2out utility, executes it on the solution stream, and
    then returns the output.

    Parameters
    ----------
    soln_stream : str
        The solution stream returned by the solver.
    ozn_file : str
        The ozn file path produced by the mzn2fzn function.
    check_complete : bool
        If True, a boolean value is returned, in addition to
        the solutions of the problem, indicating the completion status of the
        problem.

    Returns
    -------
    list or tuple
        Returns a list of solution strings. If ``check_complete=True`` the
        result is a tuple containing the solution list as first argument and a
        boolean value indicating the completion status of the problem as second
        argument.
    """
    log = get_logger(__name__)

    soln_sep = '----------'
    search_complete_msg = '=========='
    unsat_msg = '=====UNSATISFIABLE====='
    unkn_msg = '=====UNKNOWN====='
    unbnd_msg = '=====UNBOUNDED====='

    if parse_output:
        args = [config.get('solns2out', 'solns2out'), ozn_file]
        try:
            process = run(args, stdin=soln_stream)
            out = process.stdout
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err
    else:
        out = soln_stream

    lines = out.splitlines()
    solns = []
    curr_out = []
    complete = False
    for line in lines:
        line = line.strip()
        if line == soln_sep:
            soln = '\n'.join(curr_out)
            solns.append(soln)
            curr_out = []
        elif line == search_complete_msg:
            complete = True
            break
        elif line == unkn_msg:
            raise MiniZincUnknownError()
        elif line == unsat_msg:
            raise MiniZincUnsatisfiableError()
        elif line == unbnd_msg:
            raise MiniZincUnboundedError()
        else:
            curr_out.append(line)

    log.debug('Solutions found: {}', len(solns))

    if check_complete:
        return solns, complete
    return solns


class MiniZincError(RuntimeError):
    """Generic error for the MiniZinc functions."""

    def __init__(self, msg=None):
        super().__init__(msg)
        self._mzn_file = None

    @property
    def mzn_file(self):
        """str: the mzn file that generated the error."""
        return self._mzn_file

    @mzn_file.setter
    def mzn_file(self, _mzn_file):
        self._mzn_file = _mzn_file


class MiniZincUnsatisfiableError(MiniZincError):
    """Error raised when a minizinc problem is found to be unsatisfiable."""

    def __init__(self):
        super().__init__('The problem is unsatisfiable.')


class MiniZincUnknownError(MiniZincError):
    """Error raised when minizinc returns no solution (unknown)."""

    def __init__(self):
        super().__init__('The solution of the problem is unknown.')


class MiniZincUnboundedError(MiniZincError):
    """Error raised when a minizinc problem is found to be unbounded."""

    def __init__(self):
        super().__init__('The problem is unbounded.')

