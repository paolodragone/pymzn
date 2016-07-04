import os
import logging
import itertools
import contextlib

from pymzn.dzn import parse_dzn, dzn
from pymzn.bin import cmd, run, BinaryRuntimeError
from pymzn.mzn.gecode import fzn_gecode
from pymzn.mzn.model import MiniZincModel


_minizinc_instance_counter = itertools.count()


def minizinc(mzn, dzn_files=None, *, data=None, output_base=None, keep=False,
             output_vars=None, mzn_globals='gecode', fzn_fn=fzn_gecode,
             fzn_args=None, warn_on_unsolved=False, bin_path=None,
             mzn2fzn_cmd='mzn2fzn', solns2out_cmd='solns2out'):
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
                                     the model.
    :param [str] dzn_files: A list of paths to dzn files to attach to the
                            mzn2fzn execution; by default no data file is
                            attached
    :param dict data: Dictionary of variables to use as data for the solving
                      of the minizinc problem
    :param str output_base: The base name for the fzn and ozn files (extension
                            are then attached automatically); by default the
                            mzn_file name is used. If the mzn argument is
                            the content of the model, then the output base
                            is used to name the file where the mzn model
                            will be written. In that case, if output_base is
                            None then a default name ('mznout') is used.
    :param bool keep: Whether to keep the generated mzn, fzn and ozn files
    :param [str] output_vars: The list of output variables. If not provided,
                              the default list is the list of free variables
                              in the model, i.e. those variables that are
                              declared but not defined in the model
    :param str mzn_globals: The name of the directory to search for globals
                            included files in the standard library; by default
                            the 'gecode' global library is used, since Pymzn
                            assumes Gecode as default solver
    :param func fzn_fn: The function to call for the solver; defaults to the
                         function fzn_gecode
    :param dict fzn_args: A dictionary containing the additional flags to
                          pass to the fzn_cmd; default is None, meaning no
                          additional attribute
    :param bool warn_on_unsolved: Whether to log a warning message instead of
                                  raising an exception when the model is
                                  unsatisfiable, unbounded or no solution
                                  was found. In that case, the returned value
                                  will be None.
    :param str bin_path: The path to the directory containing the binaries of
                         the libminizinc utilities
    :param str mzn2fzn_cmd: The command to call to execute the mzn2fzn utility;
                            defaults to 'mzn2fzn', assuming the utility is the
                            PATH
    :param str solns2out_cmd: The command to call to execute the solns2out
                              utility; defaults to 'solns2out', assuming the
                              utility is the PATH
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
    elif isinstance(mzn, str):
        mzn_model = MiniZincModel(mzn, output_vars)
    else:
        raise TypeError('The input model is invalid.')

    mzn = mzn_model.compile()

    # Ensures isolation of instances and thread safety
    global _minizinc_instance_counter
    instance_number = next(_minizinc_instance_counter)

    output_base = output_base or mzn_model.mzn_out_file[:-4]
    output_base = '{}_{}'.format(output_base, instance_number)

    # Adjust the path if bin_path is provided
    if bin_path:
        mzn2fzn_cmd = os.path.join(bin_path, mzn2fzn_cmd)
        solns2out_cmd = os.path.join(bin_path, solns2out_cmd)

    mzn_file = output_base + '.mzn'

    try:
        # Execute mzn2fzn
        mzn_file, fzn_file, ozn_file = mzn2fzn(mzn, data=data,
                                               dzn_files=dzn_files,
                                               output_base=output_base,
                                               mzn_globals=mzn_globals,
                                               mzn2fzn_cmd=mzn2fzn_cmd)
        try:
            # Execute fzn_fn
            fzn_args = fzn_args or {}
            solns = fzn_fn(fzn_file, **fzn_args)

            # Execute solns2out
            out = solns2out(solns, ozn_file=ozn_file,
                            parse_fn=parse_dzn,
                            solns2out_cmd=solns2out_cmd)

        except (MiniZincUnknownError, MiniZincUnsatisfiableError,
                MiniZincUnboundedError) as err:
            if warn_on_unsolved:
                log.warning('No solution found. {}'.format(err.message))
                out = None
            else:
                log.exception('')
                raise
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
                os.remove(mzn_file)
                log.debug('Deleting file: %s', mzn_file)
    return out


def mzn2fzn(mzn, dzn_files=None, *, data=None, output_base=None, no_ozn=False,
            mzn_globals='gecode', mzn2fzn_cmd='mzn2fzn'):
    """
    Flatten a MiniZinc model into a FlatZinc one. It executes the mzn2fzn
    utility from libminizinc to produce a fzn and ozn files from a mzn one.

    :param str mzn: The path to a mzn file containing the MiniZinc model or
                    the content of the model.
    :param [str] dzn_files: A list of paths to dzn files to attach to the
                            mzn2fzn execution; by default no data file is
                            attached
    :param dict data: Dictionary of variables to use as data for the solving
                      of the minizinc problem
    :param str output_base: The base name for the fzn and ozn files (extension
                            are then attached automatically); by default the
                            mzn_file name is used. If the mzn argument is
                            the content of the model, then the output base
                            is used to name the file where the mzn model
                            will be written. In that case, if output_base is
                            None then a default name ('mznout') is used.
    :param bool no_ozn: Whether to create the ozn file or not. Default is
                        False (create). If no ozn is created, it is still
                        possible to use solns2out to parse the solution
                        stream output of the solver. Notice though that
                        MiniZinc optimizes the model also according to its
                        output so it is recommended to use it (if the
                        minizinc function is used, it is recommended to use
                        a model in which replace_output_stmt=True, default
                        behaviour)
    :param str mzn_globals: The name of the directory to search for globals
                            included files in the standard library; by default
                            the 'gecode' global library is used, since Pymzn
                            assumes Gecode as default solver
    :param str mzn2fzn_cmd: The command to call to execute the mzn2fzn utility;
                            defaults to 'mzn2fzn', assuming the utility is the
                            PATH
    :return: The paths to the mzn, fzn and ozn files created by the function
    :rtype: (str, str, str)
    """
    log = logging.getLogger(__name__)

    if not isinstance(mzn, str):
        raise ValueError('The input model must be a string.')

    if mzn.endswith('.mzn'):
        mzn_file = mzn
        log.debug('Mzn file provided: %s', mzn_file)
    else:
        if output_base:
            mzn_file = ''.join([output_base, '.mzn'])
            output_base = None
        else:
            mzn_file = 'mznout.mzn'

        log.debug('Writing provided content to: %s', mzn_file)
        with open(mzn_file, 'w') as f:
            f.write(mzn)

    args = []

    if output_base:
        args.append(('--output-base', output_base))

    if mzn_globals:
        args.append(('-G', mzn_globals))

    if no_ozn:
        args.append('--no-output-ozn')

    if data is not None:
        data = '"{}"'.format(' '.join(dzn(data)))
        args.append(('-D', data))

    dzn_files = dzn_files or []
    args += [mzn_file] + dzn_files

    log.debug('Calling %s with arguments: %s', mzn2fzn_cmd, args)
    cmd = cmd(mzn2fzn_cmd, args)

    try:
        run(cmd)
    except BinaryRuntimeError:
        log.exception('')
        raise

    base = output_base or mzn_file[:-4]

    fzn_file = '.'.join([base, 'fzn'])
    if not os.path.isfile(fzn_file):
        fzn_file = None

    ozn_file = '.'.join([base, 'ozn'])
    if no_ozn or not os.path.isfile(ozn_file):
        ozn_file = None

    return mzn_file, fzn_file, ozn_file


def solns2out(solns_input, ozn_file=None, *, parse_fn=None,
              solns2out_cmd='solns2out'):
    """
    Wraps the MiniZinc utility solns2out, executes it on the input solution
    stream, then parses and returns the output.

    :param str solns_input: The solution stream as output by the
                            solver, or the content of a solution file
    :param str ozn_file: The ozn file path produced by the mzn2fzn utility;
                         if None is provided (default) then the solns2out
                         utility is not used and the input stream is parsed
                         via the parse_dzn function.
    :param func parse_fn: The function that parses the output of the solns2out
                          utility, if None (default) then the solns2out
                          utility is not used and the input stream is parsed
                          via the parse_dzn function.
    :param str solns2out_cmd: The command to call to execute the solns2out
                              utility; defaults to 'solns2out', assuming the
                              utility is the PATH
    :return: A list of solutions. The solutions format depends on the parsing
             function used. The default one generates solutions represented
             as dictionaries of returned variables assignments, converted
             into their python representation (integers as ints, arrays as
             lists, ...)
    :rtype: list
    """
    log = logging.getLogger(__name__)

    soln_sep = '----------'
    search_complete_msg = '=========='
    unsat_msg = '=====UNSATISFIABLE====='
    unkn_msg = '=====UNKNOWN====='
    unbnd_msg = '=====UNBOUNDED====='

    if ozn_file and parse_fn:
        args = [ozn_file]
        log.debug('Calling %s with arguments: %s', solns2out_cmd, args)
        cmd = cmd(solns2out_cmd, args)

        try:
            out = run(cmd, stdin=solns_input)
        except BinaryRuntimeError:
            log.exception('')
            raise
    else:
        out = solns_input
        parse_fn = parse_dzn

    lines = out.split('\n')

    # To reach full stream-ability I need to pipe together the fzn with the
    # solns2out, not so trivial at this point, so I go back to return a list
    # of solutions for now, maybe in the future I will add this feature

    solns = []
    curr_out = []
    for line in lines:
        line = line.strip()
        if line == soln_sep:
            soln = parse_fn(curr_out)
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
