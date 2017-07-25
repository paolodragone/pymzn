# -*- coding: utf-8 -*-
u"""
PyMzn provides functions that mimic and enhance the tools from the libminizinc
library. With these tools, it is possible to compile a MiniZinc model into
FlatZinc, solve a given problem and get the output solutions directly into the
python code.

The main function that PyMzn provides is the ``minizinc`` function, which
executes the entire workflow for solving a CSP problem encoded in MiniZinc.
Solving a MiniZinc problem with PyMzn is as simple as::

    import pymzn
    pymzn.minizinc('test.mzn')

The ``minizinc`` function is probably the way to go for most of the problems,
but the ``mzn2fzn`` and ``solns2out`` functions are also included in the public
API to allow for maximum flexibility. The latter two functions are wrappers of
the two homonym MiniZinc tools for, respectively, converting a MiniZinc model
into a FlatZinc one and getting custom output from the solution stream of a
solver.
"""

from __future__ import with_statement
from __future__ import absolute_import
import os
import logging
import contextlib

from subprocess import CalledProcessError
from tempfile import NamedTemporaryFile

import pymzn.config as config

from . import solvers
from .solvers import gecode
from .model import MiniZincModel
from pymzn.utils import run
from pymzn.dzn import dict2dzn, dzn2dict
from itertools import imap
from io import open


class SolnStream(object):
    u"""Represents a solution stream from the `minizinc` function.

    This class can be referenced and iterated as a list.

    Arguments
    ---------
    complete : bool
        Whether the stream includes the complete set of solutions. This means
        the stream contains all solutions in a satisfiability problem, or it
        contains the global optimum for maximization/minimization problems.
    """

    def __init__(self, solns, complete):
        self._solns = solns
        self.complete = complete

    def __iter__(self):
        return iter(self._solns)

    def __getitem__(self, key):
        return self._solns[key]

    def __repr__(self):
        return u'SolnStream(solns={}, complete={})' \
                    .format(repr(self._solns), repr(self.complete))

    def __str__(self):
        return unicode(self._solns)


def minizinc(mzn, *dzn_files, **solver_args):
    if 'force_flatten' in solver_args: force_flatten = solver_args['force_flatten']; del solver_args['force_flatten']
    else: force_flatten = False
    if 'timeout' in solver_args: timeout = solver_args['timeout']; del solver_args['timeout']
    else: timeout = None
    if 'all_solutions' in solver_args: all_solutions = solver_args['all_solutions']; del solver_args['all_solutions']
    else: all_solutions = False
    if 'output_mode' in solver_args: output_mode = solver_args['output_mode']; del solver_args['output_mode']
    else: output_mode = u'dict'
    if 'solver' in solver_args: solver = solver_args['solver']; del solver_args['solver']
    else: solver = gecode
    if 'include' in solver_args: include = solver_args['include']; del solver_args['include']
    else: include = None
    if 'keep' in solver_args: keep = solver_args['keep']; del solver_args['keep']
    else: keep = False
    if 'data' in solver_args: data = solver_args['data']; del solver_args['data']
    else: data = None
    u"""Implements the workflow to solve a CSP problem encoded with MiniZinc.

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
        respectively. The latter two formats are only available if the solver
        supports them.
    all_solutions : bool
        Whether all the solutions must be returned. Notice that this can only
        be used if the solver supports returning all solutions. Default is False.
    timeout : int
        Number of seconds after which the solver should stop the computation and
        return the best solution found. This is only available if the solver has
        support for a timeout.
    force_flatten : bool
        Wheter the function should be forced to produce a flat model. Whenever
        possible, this function feeds the mzn file to the solver without passing
        through the flattener, force_flatten=True prevents this behavior and
        always produces a fzn file which is in turn passed to the solver.
    **solver_args
        Additional arguments to pass to the solver, provided as additional
        keyword arguments to this function. Check the solver documentation for
        the available arguments.

    Returns
    -------
    SolnStream
        Returns a list of solutions as a SolnStream instance. The actual content
        of the stream depends on the output_mode chosen.
    """
    log = logging.getLogger(__name__)

    if isinstance(mzn, MiniZincModel):
        mzn_model = mzn
    else:
        mzn_model = MiniZincModel(mzn)

    if output_mode != u'item':
        mzn_model.output(None)

    if not solver:
        solver = gecode
    elif isinstance(solver, unicode):
        solver = getattr(solvers, solver)

    if all_solutions and not solver.support_all:
        raise ValueError(u'The solver cannot return all solutions.')
    if timeout and not solver.support_timeout:
        raise ValueError(u'The solver does not support the timeout.')
    if output_mode == u'dzn' and not solver.support_dzn:
        raise ValueError(u'The solver does not support dzn output.')
    if output_mode == u'json' and not solver.support_json:
        raise ValueError(u'The solver does not support json output.')

    output_dir = None
    output_prefix = u'pymzn'
    if keep:
        if mzn_model.mzn_file:
            output_dir, mzn_name = os.path.split(mzn_model.mzn_file)
            output_prefix, _ = os.path.splitext(mzn_name)
        else:
            output_dir = os.getcwdu()
    output_prefix += u'_'
    output_file = NamedTemporaryFile(dir=output_dir, prefix=output_prefix,
                                     suffix=u'.mzn', delete=False, mode=u'w+',
                                     buffering=1)
    mzn_model.compile(output_file)
    mzn_file = output_file.name
    data_file = None
    fzn_file = None
    ozn_file = None

    try:
        if force_flatten or not solver.support_mzn or \
                (output_mode == u'item' and not solver.support_item):
            fzn_file, ozn_file = mzn2fzn(mzn_file, *dzn_files, data=data,
                                         keep_data=keep, include=include,
                                         no_ozn=(output_mode != u'item'))
            if output_mode in [u'item', u'dzn', u'json']:
                out = solver.solve(fzn_file, timeout=timeout,
                                   output_mode=(u'dzn' if output_mode == u'item'
                                                else output_mode),
                                   all_solutions=all_solutions, **solver_args)
                if ozn_file:
                    out = solns2out(out, ozn_file)
                    stream = SolnStream(*split_solns(out))
                else:
                    stream = SolnStream(*split_solns(out))
            else:
                out = solver.solve(fzn_file, timeout=timeout, output_mode=u'dzn',
                                   all_solutions=all_solutions, **solver_args)
                solns, complete = split_solns(out)
                solns = list(imap(dzn2dict, solns))
                stream = SolnStream(solns, complete)
        elif output_mode in [u'dzn', u'json', u'item']:
            dzn_files = list(dzn_files)
            data, data_file = process_data(mzn_file, data, keep)
            if data_file:
                dzn_files.append(data_file)
            out = solver.solve(mzn_file, *dzn_files, data=data,
                               include=include, timeout=timeout,
                               all_solutions=all_solutions,
                               output_mode=output_mode, **solver_args)
            stream = SolnStream(*split_solns(out))
        else:
            dzn_files = list(dzn_files)
            data, data_file = process_data(mzn_file, data, keep)
            if data_file:
                dzn_files.append(data_file)
            out = solver.solve(mzn_file, *dzn_files, data=data,
                        include=include, timeout=timeout, output_mode=u'item',
                        all_solutions=all_solutions, **solver_args)
            solns, complete = split_solns(out)
            solns = list(imap(dzn2dict, solns))
            stream = SolnStream(solns, complete)
    except (MiniZincUnsatisfiableError, MiniZincUnknownError,
            MiniZincUnboundedError), err:
        err.mzn_file = mzn_file
        raise err

    if not keep:
        with contextlib.suppress(FileNotFoundError):
            if data_file:
                os.remove(data_file)
                log.debug(u'Deleting file: {}'.format(data_file))
            if mzn_file:
                os.remove(mzn_file)
                log.debug(u'Deleting file: {}'.format(mzn_file))
            if fzn_file:
                os.remove(fzn_file)
                log.debug(u'Deleting file: {}'.format(fzn_file))
            if ozn_file:
                os.remove(ozn_file)
                log.debug(u'Deleting file: {}'.format(ozn_file))

    return stream


def mzn2fzn(mzn_file, *dzn_files, **_3to2kwargs):
    if 'no_ozn' in _3to2kwargs: no_ozn = _3to2kwargs['no_ozn']; del _3to2kwargs['no_ozn']
    else: no_ozn = False
    if 'include' in _3to2kwargs: include = _3to2kwargs['include']; del _3to2kwargs['include']
    else: include = None
    if 'keep_data' in _3to2kwargs: keep_data = _3to2kwargs['keep_data']; del _3to2kwargs['keep_data']
    else: keep_data = False
    if 'data' in _3to2kwargs: data = _3to2kwargs['data']; del _3to2kwargs['data']
    else: data = None
    u"""Flatten a MiniZinc model into a FlatZinc one. It executes the mzn2fzn
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
    include : str or list
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
    log = logging.getLogger(__name__)

    args = [config.get(u'mzn2fzn', u'mzn2fzn')]
    if no_ozn:
        args.append(u'--no-output-ozn')
    if include:
        if isinstance(include, unicode):
            include = [include]
        elif not isinstance(include, list):
            raise TypeError(u'The path provided is not valid.')
        for path in include:
            args.append(u'-I')
            args.append(path)

    dzn_files = list(dzn_files)
    data, data_file = process_data(mzn_file, data, keep_data)
    if data:
        args.append(u'-D')
        args.append(data)
    elif data_file:
        dzn_files.append(data_file)
    args += [mzn_file] + dzn_files

    try:
        run(args)
    except CalledProcessError, err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr)

    if not keep_data:
        with contextlib.suppress(FileNotFoundError):
            if data_file:
                os.remove(data_file)
                log.debug(u'Deleting file: {}'.format(data_file))

    mzn_base = os.path.splitext(mzn_file)[0]
    fzn_file = u'.'.join([mzn_base, u'fzn'])
    fzn_file = fzn_file if os.path.isfile(fzn_file) else None
    ozn_file = u'.'.join([mzn_base, u'ozn'])
    ozn_file = ozn_file if os.path.isfile(ozn_file) else None

    if fzn_file:
        log.debug(u'Generated file: {}'.format(fzn_file))
    if ozn_file:
        log.debug(u'Generated file: {}'.format(ozn_file))

    return fzn_file, ozn_file


def process_data(mzn_file, data, keep_data=False):
    if not data:
        return None, None

    log = logging.getLogger(__name__)
    if isinstance(data, dict):
        data = dict2dzn(data)
    elif isinstance(data, unicode):
        data = [data]
    elif not isinstance(data, list):
        raise TypeError(u'The additional data provided is not valid.')

    if keep_data or sum(imap(len, data)) >= config.get(u'dzn_width', 70):
        mzn_base, __ = os.path.splitext(mzn_file)
        data_file = mzn_base + u'_data.dzn'
        with open(data_file, u'w') as f:
            f.write(u'\n'.join(data))
        log.debug(u'Generated file: {}'.format(data_file))
        data = None
    else:
        data = u' '.join(data)
        data_file = None
    return data, data_file


def solns2out(soln_stream, ozn_file):
    u"""Wraps the solns2out utility, executes it on the solution stream, and
    then returns the output stream.

    Parameters
    ----------
    soln_stream : str
        The solution stream returned by the solver.
    ozn_file : str
        The ozn file path produced by the mzn2fzn function.

    Returns
    -------
    str
        Returns the output stream encoding the solution stream according to the
        provided ozn file.
    """
    log = logging.getLogger(__name__)
    args = [config.get(u'solns2out', u'solns2out'), ozn_file]
    try:
        process = run(args, stdin=soln_stream)
        out = process.stdout
    except CalledProcessError, err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr)
    return out


soln_sep = u'----------'
search_complete_msg = u'=========='
unsat_msg = u'=====UNSATISFIABLE====='
unkn_msg = u'=====UNKNOWN====='
unbnd_msg = u'=====UNBOUNDED====='


def split_solns(out):
    lines = out.splitlines()
    solns = []
    curr_out = []
    complete = False
    for line in lines:
        line = line.strip()
        if line == soln_sep:
            soln = u'\n'.join(curr_out)
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
    return solns, complete


class MiniZincError(RuntimeError):
    u"""Generic error for the MiniZinc functions."""

    def __init__(self, msg=None):
        super(MiniZincError, self).__init__(msg)
        self._mzn_file = None

    @property
    def mzn_file(self):
        u"""str: the mzn file that generated the error."""
        return self._mzn_file

    @mzn_file.setter
    def mzn_file(self, _mzn_file):
        self._mzn_file = _mzn_file


class MiniZincUnsatisfiableError(MiniZincError):
    u"""Error raised when a minizinc problem is found to be unsatisfiable."""

    def __init__(self):
        super(MiniZincUnsatisfiableError, self).__init__(u'The problem is unsatisfiable.')


class MiniZincUnknownError(MiniZincError):
    u"""Error raised when minizinc returns no solution (unknown)."""

    def __init__(self):
        super(MiniZincUnknownError, self).__init__(u'The solution of the problem is unknown.')


class MiniZincUnboundedError(MiniZincError):
    u"""Error raised when a minizinc problem is found to be unbounded."""

    def __init__(self):
        super(MiniZincUnboundedError, self).__init__(u'The problem is unbounded.')

