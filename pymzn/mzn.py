# -*- coding: utf-8 -*-
"""Wrapper module for the MiniZinc tool pipeline."""

import contextlib
import inspect
import logging
import os.path
import tempfile
from io import IOBase

from pymzn.binary import run, command, BinaryRuntimeError
from pymzn.dzn import dzn, parse_dzn


soln_sep_default = '----------'
search_complete_msg_default = '=========='
unsat_msg_default = '=====UNSATISFIABLE====='
unkn_msg_default = '=====UNKNOWN====='

# TODO: UNBOUNDED
# TODO: mzn2doc


def solns2out(solns_input, ozn_file, output_file=None, parse=parse_dzn,
              solns2out_cmd='solns2out', soln_sep=soln_sep_default,
              search_complete_msg=search_complete_msg_default,
              unkn_msg=unkn_msg_default, unsat_msg=unsat_msg_default):
    """
    Wraps the MiniZinc utility solns2out, executes it on the input solution
    stream, then parses and returns the output.

    :param file-like solns_input: The solution stream as output by the solver
    :param str ozn_file: The .ozn file path produced by the mzn2fzn utility
    :param str output_file: The file path where to write the output of
                            solns2out; defaults to None which outputs to
                            stdout, and thus the output is directly parsed
                            by this function and not saved on a file
    :param func parse: The function that parses the output of the solns2out
                       utility, if None a list of unparsed solution strings is
                       returned; by default the function parse_dzn is used,
                       which can be used only if no output statement is used in
                       the MiniZinc model
    :param str solns2out_cmd: The command to call to execute the solns2out
                              utility; defaults to 'solns2out', assuming the
                              utility is the PATH
    :param str soln_sep: The line separating each solution in the solver output
                         stream; defaults to the default value for solns2out
    :param str search_complete_msg: The line message for search complete in the
                                    solver output stream; defaults to the
                                    default value for solns2out
    :param str unkn_msg: The line message for unknown solution in the solver
                            output stream; defaults to the default value for
                            solns2out
    :param str unsat_msg: The line message for unsatisfiable problem in the
                          solver output stream; defaults to the default
                          value for solns2out
    :return: A list of solutions output by the solns2out utility; if a
             parsing function is provided, the solutions are parsed,
             otherwise a list of solution strings (as output by solns2out)
             is returned
    :rtype: list
    """
    log = logging.getLogger(__name__)
    args = []
    if output_file:
        args.append(('-o', output_file))
    args.append(ozn_file)

    log.debug('Calling %s with arguments: %s', solns2out_cmd, args)
    cmd = command(solns2out_cmd, args)

    try:
        out = run(cmd, cmd_in=solns_input)
    except BinaryRuntimeError:
        log.exception()
        raise

    if output_file:
        f = open(output_file)
    else:
        f = out.decode('ascii').split('\n')

    solns = []
    curr_out = []
    unsat = False
    unkn = False

    for l in f:
        l = l.strip()
        if l == soln_sep:
            if parse:
                sol = parse(curr_out)
                solns.append(sol)
                log.debug('Solution found: %s', sol)
            else:
                sol = '\n'.join(curr_out)
                solns.append(sol)
                log.debug('Solution found: %s', sol)
            curr_out = []
        elif l == search_complete_msg:
            break
        elif l == unkn_msg:
            unkn = True
            break
        elif l == unsat_msg:
            unsat = True
            break
        else:
            curr_out.append(l)

    if isinstance(f, IOBase):
        f.close()

    if unkn:
        raise MiniZincUnknownError(cmd)
    if unsat:
        raise MiniZincUnsatisfiableError(cmd)

    if len(solns) == 0:
        log.warning('A solution was found but none was returned by the '
                    'solver or the parser.')

    return solns


def mzn2fzn(mzn_file, data=None, dzn_files=None, output_base=None,
            mzn_globals=None, mzn2fzn_cmd='mzn2fzn'):
    """
    Flatten a MiniZinc model into a FlatZinc one. It executes the mzn2fzn
    utility from libmzn to produce a fzn file from a mzn one (and possibly
    an ozn file as well).

    :param str mzn_file: The path to a mzn file containing the MiniZinc model
    :param dict data: Dictionary of variables to use as data for the solving
                      of the minizinc problem
    :param [str] dzn_files: A list of paths to dzn files to attach to the
                            mzn2fzn execution; by default no data file is
                            attached
    :param str output_base: The base name for the fzn and ozn files (extension
                            are then attached automatically); by default the
                            mzn_file name is used
    :param str mzn_globals: The path to the directory to search for globals
                            included files; by default the standard global
                            library is used
    :param str mzn2fzn_cmd: The command to call to execute the mzn2fzn utility;
                            defaults to 'mzn2fzn', assuming the utility is the
                            PATH
    :return: The paths to the fzn and ozn files created by the function
    :rtype: (str, str)
    """
    log = logging.getLogger(__name__)
    args = []
    if output_base:
        args.append(('--output-base', output_base))
    if mzn_globals:
        args.append(('-G', mzn_globals))
    if data is not None:
        data = '"' + ' '.join(dzn(data)) + '"'
        args.append(('-D', data))
    dzn_files = dzn_files or []
    args += [mzn_file] + dzn_files

    log.debug('Calling %s with arguments: %s', mzn2fzn_cmd, args)
    cmd = command(mzn2fzn_cmd, args)

    try:
        run(cmd)
    except BinaryRuntimeError:
        log.exception()
        raise

    base = output_base or mzn_file[:-4]
    out_files = []

    fzn = '.'.join([base, 'fzn'])
    if os.path.isfile(fzn):
        out_files.append(fzn)
    else:
        out_files.append(None)

    ozn = '.'.join([base, 'ozn'])
    if os.path.isfile(ozn):
        out_files.append(ozn)
    else:
        out_files.append(None)

    return tuple(out_files)


def fzn_gecode(fzn_file, output_file=None, fzn_gecode_cmd='fzn-gecode',
               n_solns=-1, parallel=1, time=0, seed=0, restart=None,
               restart_base=None, restart_scale=None, suppress_segfault=False):
    """
    Solves a constrained optimization problem using the Gecode solver,
    provided a .fzn input problem file.

    :param str fzn_file: The path to the fzn file containing the problem to be
                         solved
    :param str output_file: The file where to write the solution output stream
                            of Gecode; if None (default) the stream is sent to
                            the standard output and directly returned by this
                            function, without saving it on a file
    :param str fzn_gecode_cmd: The command to call to execute the fzn-gecode
                               program; defaults to 'fzn-gecode', assuming the
                               program is the PATH
    :param int n_solns: The number of solutions to output (0 = all,
                        -1 = one/best); default is -1
    :param int parallel: The number of threads to use to solve the problem (0 =
                         #processing units); default is 1
    :param int time: The time cutoff in milliseconds, after which the
                     execution is truncated and the best solution so far is
                     returned, 0 means no time cutoff; default is 0
    :param int seed: random seed; default is 0
    :param str restart: restart sequence type; default is None
    :param str restart_base: base for geometric restart sequence; if None (
                             default) the default value of Gecode is used,
                             which is 1.5
    :param str restart_scale: scale factor for restart sequence; if None (
                              default) the default value of Gecode is used,
                              which is 250
    :param suppress_segfault: whether to accept or not a solution returned
                              when a segmentation fault has happened (this
                              is unfortunately necessary sometimes due to
                              some bugs in gecode).
    :return: A binary string containing the solution output stream of the
             execution of Gecode on the specified problem; it can be
             directly be given to the function solns2out or it can be read
             as a string using `out.decode('ascii')`
    :rtype: str
    """
    log = logging.getLogger(__name__)
    args = []
    if output_file:
        args.append(('-o', output_file))
    if n_solns >= 0:
        args.append(('-n', n_solns))
    if parallel != 1:
        args.append(('-p', parallel))
    if time > 0:
        args.append(('-time', time))
    if seed != 0:
        args.append(('-r', seed))
    if restart:
        args.append(('-restart', restart))
    if restart_base:
        args.append(('-restart-base', restart_base))
    if restart_scale:
        args.append(('-restart-scale', restart_scale))
    args.append(fzn_file)

    log.debug('Calling %s with arguments: %s', fzn_gecode_cmd, args)
    cmd = command(fzn_gecode_cmd, args)

    try:
        out = run(cmd)
    except BinaryRuntimeError as bin_err:
        if (suppress_segfault and
                bin_err.err_msg.startswith('Segmentation fault') and
                len(bin_err.out) > 0):
            log.warning('Gecode returned error code {} (segmentation fault) '
                        'but a solution was found and returned '
                        '(suppress_segfault=True).'.format(bin_err.ret))
            return bin_err.out
        else:
            log.exception('Gecode returned error code {} '
                          '(segmentation fault).'.format(bin_err.ret))
            raise bin_err

    if output_file:
        with open(output_file, 'rb') as f:
            solns = f.read()
    else:
        solns = out

    return solns


def minizinc(mzn, keep=False, bin_path=None, fzn_cmd=fzn_gecode,
             fzn_flags=None, **kwargs):
    """
    Workflow to solve a constrained optimization problem encoded with MiniZinc.
    It first calls mzn2fzn to get the fzn and ozn files, then calls the
    solver using the specified fzn_cmd, passing the fzn_flags,
    then it calls the solns2out utility on the output of the solver.

    :param str mzn_file: The mzn file specifying the problem to be solved
    :param bool keep: Whether to keep the generated fzn and ozn files or not;
                      default is False
    :param str bin_path: The path to the directory containing the binaries of
                         the libminizinc utilities
    :param func fzn_cmd: The function to call for the solver; defaults to the
                         function fzn_gecode
    :param fzn_flags: A dictionary containing the additional flags to
                      pass to the fzn_cmd; default is None, meaning no
                      additional attribute
    :param kwargs: Any additional keyword argument is passed to the mzn2fzn
                   and solns2out utilities as options
    :return: Returns the solutions as returned by the solns2out utility
    :rtype: [str] or [dict]
    """
    mzn2fzn_defaults = _get_defaults(mzn2fzn)
    mzn2fzn_kwargs = set(mzn2fzn_defaults.keys())
    mzn2fzn_args = _sub_dict(kwargs, mzn2fzn_kwargs)
    mzn2fzn_def_cmd = mzn2fzn_defaults['mzn2fzn_cmd']
    mzn2fzn_cmd = mzn2fzn_args.get('mzn2fzn_cmd', mzn2fzn_def_cmd)

    # Adjust the path if bin_path is provided
    if bin_path:
        mzn2fzn_path = os.path.join(bin_path, mzn2fzn_cmd)
        mzn2fzn_args['mzn2fzn_cmd'] = mzn2fzn_path

    # TODO: enter either a filename, or a string/stream containing the model

    if isinstance(mzn, str):
        mzn = mzn.strip()
        if mzn.endswith('.mzn'):
            mzn_file = mzn
        else:
            tempfile.NamedTemporaryFile()
    # elif isinstance(mzn, )

    # TODO: Default behaviour should be that it solves the problem without leaving any file behind, possibly without creating any files at all
    # TODO: Need to ensure isolation between each instance of the problem, even if the same mzn and fzn files are used

    # Execute mzn2fzn
    fzn, ozn = mzn2fzn(mzn_file, **mzn2fzn_args)

    if not fzn_flags:
        fzn_flags = {}

    # Execute fzn_cmd
    solns = fzn_cmd(fzn, **fzn_flags)

    if ozn:
        solns2out_defaults = _get_defaults(solns2out)
        solns2out_kwargs = set(solns2out_defaults.keys())
        solns2out_args = _sub_dict(kwargs, solns2out_kwargs)
        solns2out_def_cmd = solns2out_defaults['solns2out_cmd']
        solns2out_cmd = solns2out_args.get('solns2out_cmd', solns2out_def_cmd)

        # Adjust the path if bin_path is provided
        if bin_path:
            solns2out_path = os.path.join(bin_path, solns2out_cmd)
            solns2out_args['solns2out_cmd'] = solns2out_path

        # Execute solns2out
        out = solns2out(solns, ozn, **solns2out_args)
    else:
        # Return the raw solution strings if no ozn file produced
        out = solns

    if not keep:
        with contextlib.suppress(FileNotFoundError):
            os.remove(fzn)
            os.remove(ozn)

    return out


def _get_defaults(f):
    spec = inspect.getfullargspec(f)
    return dict(zip(reversed(spec.args), reversed(spec.defaults)))


def _sub_dict(d, keys):
    # creates a subset of d containing only the specified keys
    return {k: d[k] for k in d if k in keys}


class MiniZincUnsatisfiableError(RuntimeError):
    """
    Error raised when a minizinc problem is unsatisfiable.
    """

    def __init__(self, cmd):
        """
        :param cmd: The command executed on the unsatisfiable problem
        """
        self.cmd = cmd
        msg = 'The problem is unsatisfiable.\n{}'
        super().__init__(msg.format(self.cmd))


class MiniZincUnknownError(RuntimeError):
    """
    Error raised when minizinc returns no solution (unknown).
    """
    def __init__(self, cmd):
        """
        :param cmd: The command executed on the problem with unknown solution
        """
        self.cmd = cmd
        msg = 'The solution of the problem is unknown.\n{}'
        super().__init__(msg.format(self.cmd))
