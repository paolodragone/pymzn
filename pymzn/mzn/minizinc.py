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
import logging
import contextlib

from io import BufferedReader, TextIOWrapper
from subprocess import CalledProcessError
from tempfile import NamedTemporaryFile

import pymzn.config as config

from . import solvers
from .solvers import gecode
from .model import MiniZincModel
from ..process import Process
from ..dzn import dict2dzn, dzn2dict


class Solutions:
    """Represents a solution stream from the `minizinc` function.

    This class populates lazily but can be referenced and iterated as a list.

    Attributes
    ----------
    complete : bool
        Whether the stream includes the complete set of solutions. This means
        the stream contains all solutions in a satisfiability problem, or it
        contains the global optimum for maximization/minimization problems.
    """

    def __init__(self, stream):
        self._stream = stream
        self._solns = []
        self.complete = False
        self._iter = None
        self._stats = None

    @property
    def statistics(self):
        self._fetch_all()
        return self._stats

    def _fetch(self):
        try:
            solution = next(self._stream)
            self._solns.append(solution)
            return solution
        except StopIteration as stop:
            complete, stats = stop.value
            self.complete = complete
            if stats:
                self._stats = stats
            self._stream = None
        return None

    def _fetch_all(self):
        while self._stream:
            self._fetch()

    def __len__(self):
        self._fetch_all()
        return len(self._solns)

    def __next__(self):
        if self._stream:
            return self._fetch()
        else:
            if not self._iter:
                self._iter = iter(self._solns)
            try:
                return next(self._iter)
            except StopIteration:
                self._iter = iter(self._solns)
                raise

    def __iter__(self):
        if not self._stream:
            self._iter = iter(self._solns)
        return self

    def __getitem__(self, key):
        self._fetch_all()
        return self._solns[key]

    def __repr__(self):
        self._fetch_all()
        return repr(self._solns)

    def __str__(self):
        self._fetch_all()
        return str(self._solns)


def minizinc(
        mzn, *dzn_files, data=None, keep=False, include=None, solver=None,
        output_mode='dict', output_vars=None, output_dir=None, timeout=None,
        all_solutions=False, num_solutions=None, force_flatten=False, args=None,
        wait=True, statistics=False, **kwargs
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
    force_flatten : bool
        Wheter the function should be forced to produce a flat model. Whenever
        possible, this function feeds the mzn file to the solver without passing
        through the flattener, force_flatten=True prevents this behavior and
        always produces a fzn file which is in turn passed to the solver.
    args : dict
        Arguments for the template engine.
    wait : bool
        Whether to wait for the solving process to finish before returning the
        solution stream.
    statistics : bool
        Whether to save the statistics of the solver (if supported).
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
    if isinstance(mzn, MiniZincModel):
        mzn_model = mzn
    else:
        mzn_model = MiniZincModel(mzn)

    if not solver:
        solver = config.get('solver', gecode)
    elif isinstance(solver, str):
        solver = getattr(solvers, solver)

    if all_solutions and not solver.support_all:
        raise ValueError('The solver cannot return all solutions')
    if num_solutions is not None and not solver.support_num:
        raise ValueError('The solver cannot return a given number of solutions')
    if output_mode != 'dict' and output_vars:
        raise ValueError('Output vars only available in `dict` output mode')
    if statistics and not solver.support_stats:
        raise ValueError('The solver does not support emitting statistics')

    if not output_dir:
        output_dir = config.get('output_dir', None)

    keep = config.get('keep', keep)

    if output_mode == 'dict':
        if output_vars:
            mzn_model.dzn_output(output_vars)
            _output_mode = 'item'
        else:
            _output_mode = 'dzn'
    else:
        _output_mode = output_mode

    output_prefix = 'pymzn'
    if keep:
        mzn_dir = os.getcwd()
        if mzn_model.mzn_file:
            mzn_dir, mzn_name = os.path.split(mzn_model.mzn_file)
            output_prefix, _ = os.path.splitext(mzn_name)
        output_dir = output_dir or mzn_dir

    output_prefix += '_'
    output_file = NamedTemporaryFile(dir=output_dir, prefix=output_prefix,
                                     suffix='.mzn', delete=False, mode='w+',
                                     buffering=1)
    mzn_model.compile(output_file, rewrap=keep, args=args)
    output_file.close()

    mzn_file = output_file.name
    data_file = None
    fzn_file = None
    ozn_file = None

    force_flatten = (
           config.get('force_flatten', force_flatten)
        or not solver.support_mzn
        or (_output_mode in ['dzn', 'json'] and not solver.support_output_mode)
    )

    solver_args = {**config.get('solver_args', {}), **kwargs}
    try:
        if force_flatten:
            fzn_file, ozn_file = mzn2fzn(
                mzn_file, *dzn_files, data=data, keep_data=keep,
                include=include, globals_dir=solver.globals_dir,
                output_mode=_output_mode
            )
            solver_stream = _solve(
                solver, fzn_file, wait=wait, timeout=timeout, output_mode='dzn',
                all_solutions=all_solutions, num_solutions=num_solutions,
                statistics=statistics, **solver_args
            )
            out = solns2out(solver_stream, ozn_file)
        else:
            dzn_files = list(dzn_files)
            data, data_file = _prepare_data(mzn_file, data, keep)
            if data_file:
                dzn_files.append(data_file)
            out = _solve(
                solver, mzn_file, *dzn_files, wait=wait, lines=True, data=data,
                include=include, timeout=timeout, all_solutions=all_solutions,
                num_solutions=num_solutions, output_mode=_output_mode,
                statistics=statistics, **solver_args
            )
        solns = split_solns(out)
        if output_mode == 'dict':
            solns = _to_dict(solns)
        stream = solns
    except (
        MiniZincUnsatisfiableError, MiniZincUnknownError, MiniZincUnboundedError
    ) as err:
        err.mzn_file = mzn_file
        raise err

    cleanup_files = [] if keep else [data_file, mzn_file, fzn_file, ozn_file]
    stream = _cleanup(stream, cleanup_files)
    return Solutions(stream)


def _cleanup(stream, files):
    try:
        while True:
            yield next(stream)
    except StopIteration as stop:
        return stop.value
    finally:
        log = logging.getLogger(__name__)
        with contextlib.suppress(FileNotFoundError):
            for _file in files:
                if _file:
                    os.remove(_file)
                    log.debug('Deleting file: {}'.format(_file))


def _solve(solver, *args, lines=False, wait=False, **kwargs):
    if wait:
        out = solver.solve(*args, **kwargs)
        if lines:
            return out.splitlines()
        return out
    else:
        solver_process = solver.solve_start(*args, **kwargs)
        if lines:
            return solver_process.readlines()
        return solver_process


def mzn2fzn(mzn_file, *dzn_files, data=None, keep_data=False, globals_dir=None,
            include=None, output_mode='item', no_ozn=False):
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
    args = [config.get('mzn2fzn', 'mzn2fzn')]
    if globals_dir:
        args += ['-G', globals_dir]
    if no_ozn:
        args.append('--no-output-ozn')
    if output_mode and output_mode in ['dzn', 'json', 'item']:
        args += ['--output-mode', output_mode]
    if include:
        if isinstance(include, str):
            include = [include]
        elif not isinstance(include, list):
            raise TypeError('The path provided is not valid.')
    else:
        include = []

    include += config.get('include', [])
    for path in include:
        args += ['-I', path]

    keep_data = config.get('keep', keep_data)

    dzn_files = list(dzn_files)
    data, data_file = _prepare_data(mzn_file, data, keep_data)
    if data:
        args += ['-D', data]
    elif data_file:
        dzn_files.append(data_file)
    args += [mzn_file] + dzn_files

    log = logging.getLogger(__name__)

    process = None
    try:
        process = Process(args).run()
    except CalledProcessError as err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr) from err

    if not keep_data:
        with contextlib.suppress(FileNotFoundError):
            if data_file:
                os.remove(data_file)
                log.debug('Deleting file: {}'.format(data_file))

    mzn_base = os.path.splitext(mzn_file)[0]
    fzn_file = '.'.join([mzn_base, 'fzn'])
    fzn_file = fzn_file if os.path.isfile(fzn_file) else None
    ozn_file = '.'.join([mzn_base, 'ozn'])
    ozn_file = ozn_file if os.path.isfile(ozn_file) else None

    if fzn_file:
        log.debug('Generated file: {}'.format(fzn_file))
    if ozn_file:
        log.debug('Generated file: {}'.format(ozn_file))

    return fzn_file, ozn_file


def _prepare_data(mzn_file, data, keep_data=False):
    if not data:
        return None, None

    if isinstance(data, dict):
        data = dict2dzn(data)
    elif isinstance(data, str):
        data = [data]
    elif not isinstance(data, list):
        raise TypeError('The additional data provided is not valid.')

    log = logging.getLogger(__name__)

    if keep_data or sum(map(len, data)) >= config.get('dzn_width', 70):
        mzn_base, __ = os.path.splitext(mzn_file)
        data_file = mzn_base + '_data.dzn'
        with open(data_file, 'w') as f:
            f.write('\n'.join(data))
        log.debug('Generated file: {}'.format(data_file))
        data = None
    else:
        data = ' '.join(data)
        data_file = None
    return data, data_file


def _solns2out_process(ozn_file):
    args = [config.get('solns2out', 'solns2out'), ozn_file]
    process = Process(args)
    return process


def solns2out(stream, ozn_file):
    """Wraps the solns2out utility, executes it on the solution stream, and
    then returns the output stream.

    Parameters
    ----------
    stream : str or BufferedReader
        The solution stream returned by the solver.
    ozn_file : str
        The ozn file path produced by the mzn2fzn function.

    Returns
    -------
    generator of str
        The output stream of solns2out encoding the solution stream according to
        the provided ozn file.
    """
    log = logging.getLogger(__name__)
    args = [config.get('solns2out', 'solns2out'), ozn_file]
    process = _solns2out_process(ozn_file)
    try:
        if isinstance(stream, (BufferedReader, TextIOWrapper)):
            process.start(stream)
            yield from process.readlines()
        elif isinstance(stream, Process):
            if stream.alive:
                process.start(stream.stdout)
                yield from process.readlines()
            else:
                process.run(stream.stdout_data)
                yield from process.stdout_data.splitlines()
        else:
            process.run(stream)
            yield from process.stdout_data.splitlines()
    except CalledProcessError as err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr) from err


SOLN_SEP = '----------'
SEARCH_COMPLETE = '=========='
UNSATISFIABLE = '=====UNSATISFIABLE====='
UNKNOWN = '=====UNKNOWN====='
UNBOUNDED = '=====UNBOUNDED====='


def split_solns(lines):
    """Split the solutions from the output stream of a solver or solns2out"""
    _buffer = []
    complete = False
    for line in lines:
        line = line.strip()
        if line == SOLN_SEP:
            yield '\n'.join(_buffer)
            _buffer = []
        elif line == SEARCH_COMPLETE:
            complete = True
            _buffer = []
        elif line == UNKNOWN:
            raise MiniZincUnknownError
        elif line == UNSATISFIABLE:
            raise MiniZincUnsatisfiableError
        elif line == UNBOUNDED:
            raise MiniZincUnboundedError
        else:
            _buffer.append(line)
    return (complete, '\n'.join(_buffer))


def _to_dict(stream):
    try:
        while True:
            yield dzn2dict(next(stream))
    except StopIteration as stop:
        return stop.value


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

