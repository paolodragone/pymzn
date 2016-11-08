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
import logging
import itertools
import contextlib
from subprocess import CalledProcessError


import pymzn.config as config
from pymzn.bin import cmd, run
from pymzn import parse_dzn, dzn
from ._solvers import gecode
from ._model import Model


_sid_counter = itertools.count(1)


def minizinc(mzn, *dzn_files, data=None, keep=False, output_base=None,
             serialize=False, raw_output=False, output_vars=None,
             monitor_completion=False,
             mzn_globals_dir='gecode', fzn_fn=gecode, **fzn_args):
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
    log = logging.getLogger(__name__)

    if isinstance(mzn, Model):
        mzn_model = mzn
        mzn = mzn_model.mzn_file
    else:
        mzn_model = Model(mzn)

    if not raw_output:
        mzn_model.dzn_output_stmt(output_vars)

    mzn_base, mzn_ext = os.path.splitext(mzn)
    if mzn_ext != '.mzn':
        mzn_base = 'mznout'
    _output_base = output_base if output_base else mzn_base

    # Ensures isolation of instances and thread safety
    sid = 0 if not serialize else next(_sid_counter)
    output_file = '{}_{}.mzn'.format(_output_base, sid)

    mzn_file = mzn_model.compile(output_file)

    try:
        fzn_file, ozn_file = mzn2fzn(mzn_file, *dzn_files,
                                     data=data, keep_data=keep,
                                     mzn_globals_dir=mzn_globals_dir)
        try:
            solns = fzn_fn(fzn_file, **fzn_args)
            out = solns2out(solns, ozn_file,
                            monitor_completion=monitor_completion)
            if monitor_completion:
                out, completion_status = out
            # TODO: check if stream-ability possible now, in case remove list
            if raw_output:
                out = list(out)
            else:
                out = list(map(parse_dzn, out))
            if monitor_completion:
                return out, completion_status
            else:
                return out
        finally:
            if not keep:
                with contextlib.suppress(FileNotFoundError):
                    if fzn_file:
                        os.remove(fzn_file)
                        log.debug('Deleting file: %s', fzn_file)
                    if ozn_file:
                        os.remove(ozn_file)
                        log.debug('Deleting file: %s', ozn_file)
    finally:
        if not keep:
            with contextlib.suppress(FileNotFoundError):
                if mzn_file:
                    os.remove(mzn_file)
                    log.debug('Deleting file: %s', mzn_file)


def mzn2fzn(mzn_file, *dzn_files, data=None, keep_data=False,
            mzn_globals_dir='gecode'):
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
    log = logging.getLogger(__name__)

    args = []

    if mzn_globals_dir:
        args.append(('-G', mzn_globals_dir))

    dzn_files = list(dzn_files)

    data_file = None
    if data is not None:
        if isinstance(data, dict):
            data = dzn(data)
        elif isinstance(data, str):
            data = [data]
        elif not isinstance(data, list):
            raise TypeError('The additional data provided is not valid.')

        if keep_data or sum(map(len, data)) >= config.cmd_arg_limit:
            mzn_base, __ = os.path.splitext(mzn_file)
            data_file = mzn_base + '_data.dzn'
            with open(data_file, 'w') as f:
                f.write('\n'.join(data))
            dzn_files.append(data_file)
        else:
            data = '"{}"'.format(' '.join(data))
            args.append(('-D', data))

    args += [mzn_file] + dzn_files

    # log.debug('Calling %s with arguments: %s', config.mzn2fzn_cmd, args)

    try:
        run(cmd(config.mzn2fzn_cmd, args))
    except CalledProcessError as err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr) from err

    if not keep_data:
        with contextlib.suppress(FileNotFoundError):
            if data_file:
                os.remove(data_file)
                log.debug('Deleting file: %s', data_file)

    base = os.path.splitext(mzn_file)[0]

    fzn_file = '.'.join([base, 'fzn'])
    if not os.path.isfile(fzn_file):
        fzn_file = None

    ozn_file = '.'.join([base, 'ozn'])
    if not os.path.isfile(ozn_file):
        ozn_file = None

    log.debug('Generated files: {}, {}'.format(fzn_file, ozn_file))

    return fzn_file, ozn_file


def solns2out(solns_input, ozn_file, monitor_completion=False):
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
    log = logging.getLogger(__name__)

    soln_sep = '----------'
    search_complete_msg = '=========='
    unsat_msg = '=====UNSATISFIABLE====='
    unkn_msg = '=====UNKNOWN====='
    unbnd_msg = '=====UNBOUNDED====='

    args = [ozn_file]
    # log.debug('Calling %s with arguments: %s', config.solns2out_cmd, args)

    try:
        out = run(cmd(config.solns2out_cmd, args), stdin=solns_input)
    except CalledProcessError as err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr) from err

    # To reach full stream-ability I need to pipe together the fzn with the
    # solns2out, not so trivial at this point, so I go back to return a list
    # of solutions for now, maybe in the future I will add this feature
    search_is_complete = False
    lines = out.split('\n')
    solns = []
    curr_out = []
    for line in lines:
        line = line.strip()
        if line == soln_sep:
            soln = '\n'.join(curr_out)
            log.debug('Solution found: {}'.format(repr(soln)))
            solns.append(soln)
            curr_out = []
        elif line == search_complete_msg:
            search_is_complete = True
            break
        elif line == unkn_msg:
            raise MiniZincUnknownError()
        elif line == unsat_msg:
            raise MiniZincUnsatisfiableError()
        elif line == unbnd_msg:
            raise MiniZincUnboundedError()
        else:
            curr_out.append(line)

    if monitor_completion:
        solns = solns, search_is_complete
    return solns


class MiniZincUnsatisfiableError(RuntimeError):
    """
    Error raised when a minizinc problem is found to be unsatisfiable.
    """

    def __init__(self):
        super().__init__('The problem is unsatisfiable.')


class MiniZincUnknownError(RuntimeError):
    """
    Error raised when minizinc returns no solution (unknown).
    """

    def __init__(self):
        super().__init__('The solution of the problem is unknown.')


class MiniZincUnboundedError(RuntimeError):
    """
    Error raised when a minizinc problem is found to be unbounded.
    """

    def __init__(self):
        super().__init__('The problem is unbounded.')
