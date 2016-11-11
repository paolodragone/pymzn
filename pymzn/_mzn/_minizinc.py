"""
PyMzn provides functions that mimic and enhance the tools from the libminizinc
library. With these tools, it is possible to compile a MiniZinc model into
FlatZinc, solve a given problem and get the output solutions directly into the
python code.

The main function that PyMzn provides is the ``minizinc`` function, which
executes the entire workflow for solving a CSP problem encoded in MiniZinc.
Solving a MiniZinc problem with PyMzn is as simple as:
::

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

from pymzn._utils import get_logger
from pymzn.bin import run_cmd
from pymzn import parse_dzn, dzn, gecode
from ._model import MiniZincModel


def minizinc(mzn, *dzn_files, data=None, keep=False, output_base=None,
             globals_dir=None, stdlib_dir=None, parse_output=True, path=None,
             output_vars=None, solver=gecode, check_complete=False,
             **solver_args):
    """
    Implements the workflow to solve a CSP problem encoded with MiniZinc.

    It first calls mzn2fzn to compile the fzn and ozn files, then it calls the
    provided solver and in the end it calls the solns2out utility on the
    output of the solver.

    :param str or MinizincModel mzn: The minizinc problem to be solved.
                                     It can be either a string or an
                                     instance of MinizincModel.
                                     If it is a string, it can be either the
                                     path to the mzn file or the content of
                                     the model.
    :param dzn_files: A list of paths to dzn files to attach to the mzn2fzn
                      execution, provided as positional arguments; by default
                      no data file is attached. Data files are meant to be
                      used when there is data that is static across several
                      minizinc executions.
    :param dict data: Additional data as a dictionary of variables assignments
                      to supply to the mzn2fnz function. The dictionary is
                      then automatically converted to dzn format by the
                      pymzn.dzn function. This property is meant to include
                      data that dynamically changes across several minizinc
                      executions.
    :param bool keep: Whether to keep the generated mzn, fzn and
                      ozn files o not. Notice though that pymzn generated
                      files are not originally intended to be kept, but this
                      property can be used for debugging purpose.
                      Default is False.
    :param str output_base: The base name (including parent directories if
                            different from the working one) for the output
                            mzn, fzn and ozn files (extension are attached
                            automatically). Parent directories are not
                            created automatically so they are required to
                            exist. If None is provided (default) the name of
                            the input file is used. If the mzn input was a
                            content string, then the default name 'mznout'
                            is used.
    :param bool serialize: Whether to serialize the current workflow or not.
                           A serialized execution generates a series of mzn
                           files that do not interfere with each other,
                           thereby providing isolation of the executions.
                           This property is especially important when solving
                           multiple instances of the problem on separate
                           threads. Notice though that this attribute will
                           only guarantee the serialization of the generated
                           files, thus it will not guarantee the serialization
                           of the solving procedure and solution retrieval.
                           The default is False.
    :param bool raw_output: The default value is False. When this argument
                            is False, the output of this function is a list
                            of evaluated solutions. Otherwise, the output is
                            a list of strings containing the solutions
                            formatted according to the original output
                            statement of the model.
    :param [str] output_vars: The list of output variables. If not provided,
                              the default list is the list of free variables
                              in the model, i.e. those variables that are
                              declared but not defined in the model.
                              This argument is only used when raw_output
                              is True.
    :param bool monitor_completion: If True, the completion status of the output
                                    is returned. This is equivalent to looking at
                                    the ========== message at the end of a minizinc
                                    output.
    :param str mzn_globals_dir: The name of the directory where to search
                                for global included files in the standard
                                library; by default the 'gecode' global
                                library is used, since Pymzn assumes Gecode
                                as default solver
    :param func fzn_fn: The function to call for the solver; defaults to
                        the function pymzn.gecode
    :param dict fzn_args: A dictionary containing the additional arguments
                          to pass to the fzn_fn, provided as additional
                          keyword arguments to this function
    :return: Returns a list of solutions. If raw_input is True,
             the solutions are strings as returned from the solns2out
             function. Otherwise they are returned as dictionaries of
             variable assignments, and the values are evaluated.
    :rtype: list
    """
    log = get_logger(__name__)

    if isinstance(mzn, MiniZincModel):
        mzn_model = mzn
    else:
        mzn_model = MiniZincModel(mzn)

    if parse_output:
        mzn_model.dzn_output_stmt(output_vars)

    _globals_dir = globals_dir or solver.globals_dir

    output_dir = None
    output_prefix = 'pymzn'
    if keep:
        if output_base:
            output_dir, output_prefix = os.path.split(output_base)
        elif mzn_model.mzn_file:
            output_dir, mzn_name = os.path.split(mzn_file)
            output_prefix, mzn_ext = os.path.split(mzn_name)
    output_prefix += '_'
    output_file = NamedTemporaryFile(dir=output_dir, prefix=output_prefix,
                                     delete=False)
    mzn_model.compile(output_file)
    mzn_file = output_file.name

    fzn_file, ozn_file = mzn2fzn(mzn_file, *dzn_files, data=data,
                                 keep_data=keep, path=path,
                                 globals_dir=_globals_dir,
                                 stdlib_dir=stdlib_dir)

    if not solver.support_ozn and check_complete:
        out, complete = solver.solve(fzn_file, check_complete=True,
                                     **solver_args)
    else:
        out = solver.solve(fzn_file, **solver_args)

    if solver.support_ozn:
        try:
            if check_complete:
                solns, complete = solns2out(out, ozn_file, check_complete=True)
            else:
                solns = solns2out(out, ozn_file)
        except (MiniZincUnsatisfiableError, MiniZincUnknownError,
                MiniZincUnboundedError) as err:
            err.mzn_file = mzn_file
            raise err
    else:
        solns = out

    if parse_output:
        out = list(map(parse_dzn, out))

    if not keep:
        with contextlib.suppress(FileNotFoundError):
            if mzn_file:
                os.remove(mzn_file)
                log.debug('Deleting file: %s', mzn_file)
            if fzn_file:
                os.remove(fzn_file)
                log.debug('Deleting file: %s', fzn_file)
            if ozn_file:
                os.remove(ozn_file)
                log.debug('Deleting file: %s', ozn_file)

    if check_complete:
        return solns, complete
    return solns


def mzn2fzn(mzn_file, *dzn_files, data=None, keep_data=False, globals_dir=None,
            stdlib_dir=None, path=None, no_ozn=False):
    """
    Flatten a MiniZinc model into a FlatZinc one. It executes the mzn2fzn
    utility from libminizinc to produce a fzn and ozn files from a mzn one.

    :param str mzn_file: The path to the mzn file containing model.
    :param [str] dzn_files: A list of paths to dzn files to attach to the
                            mzn2fzn execution, provided as additional
                            positional arguments to this function
    :param dict data: Dictionary of variables to use as inline data
    :param bool keep_data: If true, the inline data is written to a dzn file.
                           Default is False.
    :param str mzn_globals_dir: The name of the directory where to search
                                for global included files in the standard
                                library; by default the 'gecode' global
                                library is used, since Pymzn assumes Gecode
                                as default solver
    :return: The paths to the fzn and ozn files created by the function
    :rtype: (str, str)
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

        if keep_data or sum(map(len, data)) >= config.get('arg_limit', 80):
            mzn_base, __ = os.path.splitext(mzn_file)
            data_file = mzn_base + '_data.dzn'
            with open(data_file, 'w+b') as f:
                f.write('\n'.join(data))
            dzn_files.append(data_file)
            log.debug('Generated file: {}', data_file)
        else:
            data = '"{}"'.format(' '.join(data))
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
                log.debug('Deleting file: %s', data_file)

    mzn_base = os.path.splitext(mzn_file)[0]
    fzn_file = '.'.join([mzn_base, 'fzn']) if os.path.isfile(fzn_file) else None
    ozn_file = '.'.join([mzn_base, 'ozn']) if os.path.isfile(ozn_file) else None
    if fzn_file:
        log.debug('Generated file: {}', fzn_file)
    if ozn_file:
        log.debug('Generated file: {}', ozn_file)

    return fzn_file, ozn_file


def solns2out(solver_output, ozn_file, check_complete=False):
    """
    Wraps the solns2out utility, executes it on the input solution stream,
    and then returns the output.

    :param str solns_input: The solution stream as output by the
                            solver, or the content of a solution file
    :param str ozn_file: The ozn file path produced by the mzn2fzn utility
    :param bool monitor_completion: If True, the completion status of the output
                                    is returned. This is equivalent to looking at
                                    the ========== message at the end of a minizinc
                                    output.
    :return: A list of solutions as strings. The user needs to take care of
             the parsing. If the output is in dzn format one can use the
             parse_dzn function.
    :rtype: list of str
    """
    log = get_logger(__name__)

    soln_sep = '----------'
    search_complete_msg = '=========='
    unsat_msg = '=====UNSATISFIABLE====='
    unkn_msg = '=====UNKNOWN====='
    unbnd_msg = '=====UNBOUNDED====='

    args = [config.get('solns2out', 'solns2out'), ozn_file]

    try:
        process = run(args, stdin=solver_output)
        out = process.stdout
    except CalledProcessError as err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr) from err

    lines = out.split('\n')
    solns = []
    curr_out = []
    complete = False
    for line in lines:
        line = line.strip()
        if line == soln_sep:
            soln = '\n'.join(curr_out)
            log.debug('Solution found: {}'.format(repr(soln)))
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

    if check_complete:
        return solns, complete
    return solns


class MiniZincError(RuntimeError):

    def __init__(self, msg=None):
        super().__init__(msg)
        self._mzn_file = None

    @property
    def mzn_file(self):
        return self._mzn_file

    @mzn_file.setter
    def mzn_file(self, _mzn_file):
        self._mzn_file = _mzn_file


class MiniZincUnsatisfiableError(MiniZincError):
    """
    Error raised when a minizinc problem is found to be unsatisfiable.
    """

    def __init__(self):
        super().__init__('The problem is unsatisfiable.')


class MiniZincUnknownError(MiniZincError):
    """
    Error raised when minizinc returns no solution (unknown).
    """

    def __init__(self):
        super().__init__('The solution of the problem is unknown.')


class MiniZincUnboundedError(MiniZincError):
    """
    Error raised when a minizinc problem is found to be unbounded.
    """

    def __init__(self):
        super().__init__('The problem is unbounded.')

