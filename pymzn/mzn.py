# -*- coding: utf-8 -*-
"""Wrapper module for the MiniZinc tool pipeline."""
import ast
import contextlib
import itertools
import logging
import os.path
import re

from pymzn.binary import run, command, BinaryRuntimeError
from pymzn.dzn import dzn, dzn_value, parse_dzn

# TODO: mzn2doc
# TODO: optimatsat
# TODO: continue with the solutions as streams
# TODO: isolation for dzns

_minizinc_instance_counter = itertools.count()


class MinizincModel(object):
    """
    Wraps a minizinc model.

    Can use a mzn file as template and add variables, constraints and modify
    the solve statement. The output statement can be replaced by a
    pymzn-friendly one when using the minizinc function.
    The final model is a string combining the existing model (if provided)
    and the updates performed on the MinizincModel instance.
    """

    _output_stmt_p = re.compile('output.+?;', re.S)
    _free_var_p = re.compile('.+?var[^:]+?:\s*(\w+)\s*;', re.S)
    _free_var_type_p = re.compile('.+?var.+?', re.S)
    _solve_stmt_p = re.compile('solve.+?;', re.S)

    def __init__(self, mzn=None, output_vars=None, *,
                 replace_output_stmt=True):
        """
        :param str or MinizincModel mzn: The minizinc problem template.
                                         It can be either a string or an
                                         instance of MinizincModel. If it is
                                         a string, it can be either the path
                                         to the mzn file or the content of
                                         the model.
        :param [str] output_vars: The list of output variables. If not
                                  provided, the default list is the list of
                                  free variables in the model, i.e. those
                                  variables that are declared but not
                                  defined in the model
        :param bool replace_output_stmt: Whether to replace the output
                                         statement with the pymzn default
                                         one (used to parse the solutions
                                         with solns2out with the default
                                         parser)
        """
        self.mzn = mzn
        self.mzn_out_file = ''
        self.output_vars = output_vars if output_vars else []
        self.replace_output_stmt = replace_output_stmt
        self.vars = {}
        self.constraints = []
        self.solve_stmt = None
        self._log = logging.getLogger(__name__)

    def constraint(self, constr, comment=None):
        """
        Adds a constraint to the current model.

        :param str constr: The content of the constraint, i.e. only the actual
                           constraint without the starting 'constraint' and
                           the ending semicolon
        :param str comment: A comment to attach to the constraint
        """
        self.constraints.append((constr, comment))

    def solve(self, solve_stmt, comment=None):
        """
        Updates the solve statement of the model.

        :param str solve_stmt: The content of the solve statement, i.e. only
                               the solving expression (and possible
                               annotations) without the starting 'solve' and
                               the ending semicolon
        :param str comment: A comment to attach to the statement
        """
        self.solve_stmt = (solve_stmt, comment)

    def var(self, vartype, var, val=None, comment=None):
        """
        Adds a variable (or parameter) to the model.

        :param str vartype: The type of the variable (in the minizinc
                            language), including 'var' if a variable.
        :param str var: The name of the variable
        :param any val: The value of the variable if any. It can be any value
                        convertible to dzn through the dzn_value function
        :param str comment: A comment to attach to the variable declaration
                            statement
        """
        self.vars[var] = (vartype, dzn_value(val), comment)

    @staticmethod
    def _pymzn_output_stmt(output_vars):
        out_var = '"\'{0}\':", show({0})'
        out_list = ', '.join([out_var.format(var) for var in output_vars])
        return ''.join(['output [ "{", ', out_list, ' "}" ];'])

    def compile(self):
        """
        Compiles the model. The compiled model contains the content of the
        template (if provided) plus the added variables and constraints. The
        solve statement will be replaced if provided a new one and the
        output statement will be replaced with a pymzn-friendly one if
        replace_output_stmt=True.

        :return: A string containing the compiled model.
        """
        model = ""
        gen = True

        if self.mzn:
            if isinstance(self.mzn, str):
                if self.mzn.endswith('.mzn'):
                    with open(self.mzn) as f:
                        model = f.read()
                    self.mzn_out_file = self.mzn
                else:
                    model = self.mzn
                    self.mzn_out_file = 'mznout.mzn'
            elif isinstance(self.mzn, MinizincModel):
                model = self.mzn.compile()
                gen = False
            else:
                self._log.warning('The provided value for file_mzn is valid. '
                                  'It will be ignored.')

        if not self.output_vars:
            free_vars = MinizincModel._free_var_p.findall(model)
            self.output_vars.append(free_vars)

        lines = ['\n%% GENERATED BY PYMZN %%\n\n'] if gen else ['\n\n\n']

        for var, (vartype, val, comment) in self.vars.items():
            comment and lines.append('% {}'.format(comment))
            if val is not None:
                lines.append('{}: {} = {};'.format(vartype, var, val))
            else:
                lines.append('{}: {};'.format(vartype, var))
                if MinizincModel._free_var_type_p.match(vartype):
                    self.output_vars.append(var)

        lines.append('\n')
        for i, (constr, comment) in self.constraints:
            comment and lines.append('% {}'.format(comment))
            lines.append('constraint {};'.format(constr))

        if self.solve_stmt is not None:
            model = MinizincModel._solve_stmt_p.sub('', model)
            solve_stmt, comment = self.solve_stmt
            lines.append('\n')
            comment and lines.append('% {}'.format(comment))
            lines.append('solve {};'.format(solve_stmt))

        if not self.output_vars:
            raise RuntimeError('The model has no output variable.')

        if self.replace_output_stmt:
            model = MinizincModel._output_stmt_p.sub('', model)
            lines.append('\n')
            output_stmt = self._pymzn_output_stmt(self.output_vars)
            lines.append(output_stmt)
            lines.append('\n')

        model += '\n'.join(lines)
        return model


def solns2out(solns_input, ozn_file=None, *, parse_fn=None,
              solns2out_cmd='solns2out'):
    """
    Wraps the MiniZinc utility solns2out, executes it on the input solution
    stream, then parses and returns the output.

    :param str or bytes solns_input: The solution stream as output by the
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
        cmd = command(solns2out_cmd, args)

        try:
            out = run(cmd, cmd_in=solns_input)
        except BinaryRuntimeError:
            log.exception('')
            raise
    else:
        out = solns_input
        parse_fn = parse_dzn

    if isinstance(out, bytes):
        out = out.decode('ascii')
    lines = out.split('\n')

    curr_out = []
    for line in lines:
        line = line.strip()
        if line == soln_sep:
            soln = parse_fn(curr_out)
            log.debug('Solution found: %s', soln)
            yield soln
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
            mzn_file = os.path.join(output_base, '.mzn')
            output_base = None
        else:
            mzn_file = 'mznout.mzn'

        log.debug('Writing provided content to: %s', mzn_file)
        with open(mzn_file) as f:
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
    cmd = command(mzn2fzn_cmd, args)

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
    if no_ozn or os.path.isfile(ozn_file):
        ozn_file = None

    return mzn_file, fzn_file, ozn_file


def fzn_gecode(fzn_file, *, time=0, parallel=1, n_solns=-1, seed=0,
               fzn_gecode_cmd='fzn-gecode', suppress_segfault=False,
               restart=None, restart_base=None, restart_scale=None):
    """
    Solves a constrained optimization problem using the Gecode solver,
    provided a .fzn input problem file.

    :param str fzn_file: The path to the fzn file containing the problem to
                         be solved
    :param str fzn_gecode_cmd: The command to call to execute the fzn-gecode
                               program; defaults to 'fzn-gecode', assuming
                               the program is the PATH
    :param int n_solns: The number of solutions to output (0 = all,
                        -1 = one/best); default is -1
    :param int parallel: The number of threads to use to solve the problem
                         (0 = #processing units); default is 1
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
    :param bool suppress_segfault: whether to accept or not a solution
                                   returned when a segmentation fault has
                                   happened (this is unfortunately necessary
                                   sometimes due to some bugs in gecode).
    :return: A binary string (bytes) containing the solution output stream
             of the execution of Gecode on the specified problem; it can be
             directly be given to the function solns2out or it can be read
             as a string using `out.decode('ascii')`
    :rtype: str
    """
    log = logging.getLogger(__name__)
    args = []
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

    assert os.path.isfile(fzn_file), 'Input fzn file does not exists.'

    log.debug('Calling %s with arguments: %s', fzn_gecode_cmd, args)
    cmd = command(fzn_gecode_cmd, args)

    try:
        solns = run(cmd)
    except BinaryRuntimeError as bin_err:
        err_msg = bin_err.err_msg
        if (suppress_segfault and len(bin_err.out) > 0 and
                err_msg.startswith('Segmentation fault')):
            log.warning('Gecode returned error code {} (segmentation '
                        'fault) but a solution was found and returned '
                        '(suppress_segfault=True).'.format(bin_err.ret))
            solns = bin_err.out
        else:
            log.exception('Gecode returned error code {} '
                          '(segmentation fault).'.format(bin_err.ret))
            raise bin_err
    return solns


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

    if isinstance(mzn, MinizincModel):
        mzn_model = mzn
    elif isinstance(mzn, str):
        mzn_model = MinizincModel(mzn, output_vars)
    else:
        raise TypeError('The input model is invalid.')

    # Ensures isolation of instances and thread safety
    global _minizinc_instance_counter
    instance_number = _minizinc_instance_counter.netx()

    output_base = output_base or mzn_model.mzn_out_file[:-4]
    output_base = '{}_{}'.format(output_base, instance_number)

    # Adjust the path if bin_path is provided
    if bin_path:
        mzn2fzn_cmd = os.path.join(bin_path, mzn2fzn_cmd)
        solns2out_cmd = os.path.join(bin_path, solns2out_cmd)

    # Execute mzn2fzn
    mzn_file, fzn_file, ozn_file = mzn2fzn(mzn_model.compile(), data=data,
                                           dzn_files=dzn_files,
                                           output_base=output_base,
                                           mzn_globals=mzn_globals,
                                           mzn2fzn_cmd=mzn2fzn_cmd)
    try:
        # Execute fzn_fn
        fzn_args = fzn_args or {}
        solns = fzn_fn(fzn_file, **fzn_args)

        # Execute solns2out
        out = solns2out(solns, ozn_file=ozn_file, parse_fn=ast.literal_eval,
                        solns2out_cmd=solns2out_cmd)

    except (MiniZincUnsatisfiableError, MiniZincUnknownError,
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
                os.remove(mzn_file)
                fzn_file and os.remove(fzn_file)
                ozn_file and os.remove(ozn_file)
                log.debug('Deleting files: %s %s %s',
                          mzn_file, fzn_file, ozn_file)
    return out


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
