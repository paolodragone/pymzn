import contextlib
import logging
import os
from subprocess import CalledProcessError

import pymzn.config as config
from pymzn.bin import cmd, run
from pymzn.dzn import parse_dzn, dzn
from pymzn.mzn.model import MiniZincModel
from pymzn.mzn.solvers import gecode

# TODO: check all the docstrings


def minizinc(mzn, *dzn_files, data=None, serialize=False, raw_output=False,
             keep=False, output_base=None, output_vars=None,
             mzn_globals_dir='gecode', fzn_fn=gecode, **fzn_args):
    """
    Workflow to solve a constrained optimization problem encoded with MiniZinc.
    It first calls mzn2fzn to get the fzn and ozn files, then calls the
    solver using the specified fzn_cmd, passing the fzn_flags,
    then it calls the solns2out utility on the output of the solver.

    :param str or MinizincModel mzn: The minizinc problem to be solved.
                                     It can be either a string or an
                                     instance of MinizincModel.
                                     If it is a string, it can be either the
                                     path to the mzn file or the content of
                                     the _model.
    :param str *args dzn_files: A list of paths to dzn files to attach to
                                the mzn2fzn execution; by default no data
                                file is attached
    :param dict data: Dictionary of variables to use as data for the solving
                      of the minizinc problem
    :param str output_base: The base name for the fzn and ozn files (extension
                            are then attached automatically); by default the
                            mzn_file name is used. If the mzn argument is
                            the content of the _model, then the output base
                            is used to name the file where the mzn _model
                            will be written. In that case, if output_base is
                            None then a default name ('mznout') is used.
    :param bool keep: Whether to keep the generated mzn, fzn and ozn files
    :param [str] output_vars: The list of output variables. If not provided,
                              the default list is the list of free variables
                              in the _model, i.e. those variables that are
                              declared but not defined in the _model
    :param str mzn_globals_dir: The name of the directory to search for
                                globals included files in the standard
                                library; by default the 'gecode' global
                                library is used, since Pymzn assumes Gecode
                                as default solver
    :param func fzn_fn: The function to call for the solver; defaults to the
                         function fzn_gecode
    :param dict fzn_args: A dictionary containing the additional flags to
                          pass to the fzn_cmd; default is None, meaning no
                          additional attribute
    :return: Returns the solutions as returned by the solns2out utility.
             The solutions format depends on the parsing function used.
             The default one generates solutions represented  as dictionaries
             of returned variables assignments, converted  into their python
             representation (integers as ints, arrays as lists, ...)
    :rtype: list
    """
    log = logging.getLogger(__name__)

    if isinstance(mzn, MiniZincModel):
        mzn_model = mzn
    else:
        mzn_model = MiniZincModel(mzn, output_base=output_base,
                                  serialize=serialize)
    if not raw_output:
        mzn_model.dzn_output_stmt(output_vars)
    mzn_file = mzn_model.compile()

    try:
        fzn_file, ozn_file = mzn2fzn(mzn_file, *dzn_files, data=data,
                                     mzn_globals_dir=mzn_globals_dir)
        try:
            solns = fzn_fn(fzn_file, **fzn_args)
            out = solns2out(solns, ozn_file)
            # TODO: check if stream-ability possible now, in case remove list
            return list(map(parse_dzn, out))
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


def mzn2fzn(mzn_file, *dzn_files, data=None, mzn_globals_dir='gecode'):
    """
    Flatten a MiniZinc _model into a FlatZinc one. It executes the mzn2fzn
    utility from libminizinc to produce a fzn and ozn files from a mzn one.

    :param str mzn_file: The path to a mzn file containing the MiniZinc
    _model or
                    the content of the _model.
    :param [str] dzn_files: A list of paths to dzn files to attach to the
                            mzn2fzn execution; by default no data file is
                            attached
    :param dict data: Dictionary of variables to use as data for the solving
                      of the minizinc problem
    :param str output_base: The base name for the fzn and ozn files (extension
                            are then attached automatically); by default the
                            mzn_file name is used. If the mzn argument is
                            the content of the _model, then the output base
                            is used to name the file where the mzn _model
                            will be written. In that case, if output_base is
                            None then a default name ('mznout') is used.
    :param str mzn_globals_dir: The name of the directory to search for
                                globals included files in the standard
                                library; by default the 'gecode' global
                                library is used, since Pymzn assumes Gecode
                                as default solver
    :return: The paths to the mzn, fzn and ozn files created by the function
    :rtype: (str, str)
    """
    log = logging.getLogger(__name__)

    args = []

    if mzn_globals_dir:
        args.append(('-G', mzn_globals_dir))

    if data is not None:
        data = '"{}"'.format(' '.join(dzn(data)))
        args.append(('-D', data))

    dzn_files = dzn_files or []
    args += [mzn_file] + dzn_files

    log.debug('Calling %s with arguments: %s', config.mzn2fzn_cmd, args)

    try:
        run(cmd(config.mzn2fzn_cmd, args))
    except CalledProcessError as err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr) from err

    base = os.path.splitext(mzn_file)[0]

    fzn_file = '.'.join([base, 'fzn'])
    if not os.path.isfile(fzn_file):
        fzn_file = None

    ozn_file = '.'.join([base, 'ozn'])
    if not os.path.isfile(ozn_file):
        ozn_file = None

    return fzn_file, ozn_file


def solns2out(solns_input, ozn_file=None):
    """
    Wraps the MiniZinc utility solns2out, executes it on the input solution
    stream, and then returns the output.

    :param str solns_input: The solution stream as output by the
                            solver, or the content of a solution file
    :param str ozn_file: The ozn file path produced by the mzn2fzn utility;
                         if None is provided (default) then the solns2out
                         utility is not used and the input stream is parsed
                         via the parse_dzn function
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

    if ozn_file:
        args = [ozn_file]
        log.debug('Calling %s with arguments: %s', config.solns2out_cmd, args)

        try:
            out = run(cmd(config.solns2out_cmd, args), stdin=solns_input)
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err
    else:
        out = solns_input

    lines = out.split('\n')

    # To reach full stream-ability I need to pipe together the fzn with the
    # solns2out, not so trivial at this point, so I go back to return a list
    # of solutions for now, maybe in the future I will add this feature

    solns = []
    curr_out = []
    for line in lines:
        line = line.strip()
        if line == soln_sep:
            soln = '\n'.join(curr_out)
            log.debug('Solution found: %s', soln)
            solns.append(soln)
            curr_out = []
        elif line == search_complete_msg:
            break
        elif line == unkn_msg:
            raise MiniZincUnknownError()
        elif line == unsat_msg:
            raise MiniZincUnsatisfiableError()
        elif line == unbnd_msg:
            raise MiniZincUnboundedError()
        else:
            curr_out.append(line)
    return solns


class MiniZincUnsatisfiableError(RuntimeError):
    """
    Error raised when a minizinc problem is unsatisfiable.
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
    Error raised when a minizinc problem is unbounded.
    """

    def __init__(self):
        super().__init__('The problem is unbounded.')
