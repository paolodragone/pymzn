# -*- coding: utf-8 -*-
u"""Provides classes to interface solvers with PyMzn.

PyMzn interfaces with solvers through the ``Solver`` class. This class includes
the necessary infomation for PyMzn to setup the solver. This class also includes
the ``solve`` method which takes care of the actual solving of a
MiniZinc/FlatZinc model. The solvers classes are subclasses of the ``Solver``
class, providing implementations of the ``solve`` method.
PyMzn provides a number of solver implementations out-of-the-box.
PyMzn's default solver is Gecode, which class is `pymzn.Gecode` and the default
instance is ``pymzn.gecode``.

To use a different solver or to exend an existing one, one has to subclass the
Solver class and implement the ``solve`` method.

For instance::

    from pymzn import Solver
    from pymzn.utils import run

    class MySolver(Solver):
        def __init__(self, path='/path/to/solver'):
            super().__init__()
            self.cmd = path

        @property
        def support_mzn(self):
            return False

        @property
        def support_dzn(self):
            return True

        @property
        def support_json(self):
            return False

        @property
        def support_item(self):
            return False

        @property
        def support_dict(self):
            return False

        @property
        def support_all(self):
            return False

        @property
        def support_timeout(self):
            return False

        # You can ignore the dzn_files, data and include if the solver does not
        # support mzn inputs. Similarly, you can ignore timeout and
        # all_solutions if the solver does not support the timeout and returning
        # all solutions respectively. Check out the Gecode implementation for
        # an example of how to handle these parameters if needed.
        def solve(self, mzn_file, *dzn_files, data=None, include=None,
                  timeout=None, all_solutions=False, output_mode='dzn',
                  arg1=def_val1, arg2=def_val2, **kwargs):
        # mzn_file contains a fzn if the solver does not support mzn inputs
        args = [self.path, '-arg1', arg1, '-arg2', arg2, mzn_file]
        process = run(args)
        return process.stdout    # assuming the solver returns dzn solutions


Then one can run the ``minizinc`` function with the custom solver::

    my_solver = MySolver()
    pymzn.minizinc('test.mzn', solver=my_solver(), arg1=val1, arg2=val2)
"""

from __future__ import division
from __future__ import absolute_import
import re
import logging

import pymzn.config as config

from pymzn.utils import run
from abc import ABC, abstractmethod
from subprocess import CalledProcessError


class Solver(ABC):
    u"""Abstract solver class.

    All the solvers inherit from this base class.

    Parameters
    ----------
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, globals_dir=u'std'):
        self.globals_dir = globals_dir

    @property
    @abstractmethod
    def support_mzn(self):
        u"""Whether the solver supports direct mzn input"""

    @property
    @abstractmethod
    def support_dzn(self):
        u"""Whether the solver supports dzn output"""

    @property
    @abstractmethod
    def support_json(self):
        u"""Whether the solver supports json output"""

    @property
    @abstractmethod
    def support_item(self):
        u"""Whether the solver supports item output"""

    @property
    @abstractmethod
    def support_dict(self):
        u"""Whether the solver supports dict output"""

    @property
    @abstractmethod
    def support_all(self):
        u"""Whether the solver supports collecting all solutions"""

    @property
    @abstractmethod
    def support_timeout(self):
        u"""Whether the solver supports a timeout"""

    @abstractmethod
    def solve(self, mzn_file, *dzn_files, **kwargs):
        if 'output_mode' in kwargs: output_mode = kwargs['output_mode']; del kwargs['output_mode']
        else: output_mode = u'dzn'
        if 'all_solutions' in kwargs: all_solutions = kwargs['all_solutions']; del kwargs['all_solutions']
        else: all_solutions = False
        if 'timeout' in kwargs: timeout = kwargs['timeout']; del kwargs['timeout']
        else: timeout = None
        if 'include' in kwargs: include = kwargs['include']; del kwargs['include']
        else: include = None
        if 'data' in kwargs: data = kwargs['data']; del kwargs['data']
        else: data = None
        u"""Solve a problem encoded with MiniZinc/FlatZinc.

        This method should call an external solver, wait for the solution and
        provide the output of the solver. If the solver does not have a Python
        interface, the ``pymzn.util.run`` module can be used to run external
        executables.

        If a solver supports neither dzn nor json output, then its PyMzn
        implementation should take care of parsing the solver output and return
        a SolnsStream with solutions evaluated as dictionaries.

        Parameters
        ----------
        mzn_file : str
            The path to the mzn file to solve.
        dzn_files
            A list of paths to dzn files.
        data : str
            A dzn string containing additional inline data to pass to the solver.
        include : str or [str]
            A path or a list of paths to included files.
        timeout : int
            The timeout for the solver. If None, no timeout given.
        all_solutions : bool
            Whether to return all solutions.
        output_mode : 'dzn', 'json', 'item', 'dict'
            The output mode required.

        Returns
        -------
        str or SolnsStream
            The output of the solver if output_mode in ['dzn', 'json', 'item']
            or a SolnsStream of evaluated solutions if output_mode == 'dict'.
        """


class Gecode(Solver):
    u"""Interface to the Gecode solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn-gecode executable.
    fzn_path : str
        The path to the fzn-gecode executable.
    globals_dir : str
        The path to the directory for global included files.
    """
    def __init__(self, mzn_path=u'mzn-gecode', fzn_path=u'fzn-gecode',
                 globals_dir=u'gecode'):
        super(Gecode, self).__init__(globals_dir)
        self.mzn_cmd = mzn_path
        self.fzn_cmd = fzn_path

    @property
    def support_mzn(self):
        u"""Whether the solver supports direct mzn input"""
        return True

    @property
    def support_dzn(self):
        u"""Whether the solver supports dzn output"""
        return True

    @property
    def support_json(self):
        u"""Whether the solver supports json output"""
        return False

    @property
    def support_item(self):
        u"""Whether the solver supports item output"""
        return True

    @property
    def support_dict(self):
        u"""Whether the solver supports dict output"""
        return False

    @property
    def support_all(self):
        u"""Whether the solver supports collecting all solutions"""
        return True

    @property
    def support_timeout(self):
        u"""Whether the solver supports a timeout"""
        return True

    def solve(self, mzn_file, *dzn_files, **kwargs):
        if 'suppress_segfault' in kwargs: suppress_segfault = kwargs['suppress_segfault']; del kwargs['suppress_segfault']
        else: suppress_segfault = False
        if 'seed' in kwargs: seed = kwargs['seed']; del kwargs['seed']
        else: seed = 0
        if 'parallel' in kwargs: parallel = kwargs['parallel']; del kwargs['parallel']
        else: parallel = 1
        if 'output_mode' in kwargs: output_mode = kwargs['output_mode']; del kwargs['output_mode']
        else: output_mode = u'item'
        if 'all_solutions' in kwargs: all_solutions = kwargs['all_solutions']; del kwargs['all_solutions']
        else: all_solutions = False
        if 'timeout' in kwargs: timeout = kwargs['timeout']; del kwargs['timeout']
        else: timeout = None
        if 'include' in kwargs: include = kwargs['include']; del kwargs['include']
        else: include = None
        if 'data' in kwargs: data = kwargs['data']; del kwargs['data']
        else: data = None
        u"""Solve a MiniZinc/FlatZinc problem with Gecode.

        Parameters
        ----------
        mzn_file : str
            The path to the mzn file to solve.
        dzn_files
            A list of paths to dzn files.
        data : str
            A dzn string containing additional inline data to pass to the solver.
        include : str or [str]
            A path or a list of paths to included files.
        timeout : int
            The timeout for the solver. If None, no timeout given.
        all_solutions : bool
            Whether to return all solutions.
        output_mode : 'dzn', 'json', 'item', 'dict'
            The output mode required.
        parallel : int
            The number of threads to use to solve the problem
            (0 = #processing units); default is 1.
        seed : int
            Random seed.
        suppress_segfault : bool
            Whether to accept or not a solution returned when a segmentation
            fault has happened (this is unfortunately necessary sometimes due to
            some bugs in Gecode).
        Returns
        -------
        str
            The output of the solver.
        """
        log = logging.getLogger(__name__)

        mzn = True
        args = []
        if mzn_file.endswith(u'fzn'):
            if output_mode != u'dzn':
                raise ValueError(u'Only dzn output available with fzn input.')
            args.append(self.fzn_cmd)
        else:
            if output_mode != u'item':
                raise ValueError(u'Only item output available with mzn input.')
            mzn = True
            args.append(self.mzn_cmd)
            args.append(u'-G')
            args.append(self.globals_dir)
            if include:
                if isinstance(include, unicode):
                    include = [include]
                for path in include:
                    args.append(u'-I')
                    args.append(path)
            if data:
                args.append(u'-D')
                args.append(data)

        fzn_flags = []
        if all_solutions:
            args.append(u'-a')
        if parallel != 1:
            fzn_flags.append(u'-p')
            fzn_flags.append(unicode(parallel))
        if timeout and timeout > 0:
            fzn_flags.append(u'-time')
            fzn_flags.append(unicode(timeout * 1000)) # Gecode takes milliseconds
        if seed != 0:
            fzn_flags.append(u'-r')
            fzn_flags.append(unicode(seed))
        if mzn and fzn_flags:
            args.append(u'--fzn-flags')
            args.append(u'{}'.format(u' '.join(fzn_flags)))
        else:
            args += fzn_flags
        args.append(mzn_file)
        if mzn and dzn_files:
            for dzn_file in dzn_files:
                args.append(dzn_file)

        try:
            process = run(args)
            out = process.stdout
        except CalledProcessError, err:
            if suppress_segfault:
                log.warning(u'Gecode returned error code {} (segmentation '
                            u'fault) but a solution was found and returned '
                            u'(suppress_segfault=True).'.format(err.returncode))
                out = err.stdout
            else:
                log.exception(err.stderr)
                raise RuntimeError(err.stderr)
        return out


class Chuffed(Solver):
    u"""Interface to the Chuffed solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn-chuffed executable.
    fzn_path : str
        The path to the fzn-chuffed executable.
    globals_dir : str
        The path to the directory for global included files.
    """
    def __init__(self, mzn_path=u'mzn-chuffed', fzn_path=u'fzn-chuffed',
                 globals_dir=u'chuffed'):
        super(Chuffed, self).__init__(globals_dir)
        self.mzn_cmd = mzn_path
        self.fzn_cmd = fzn_path

    @property
    def support_mzn(self):
        u"""Whether the solver supports direct mzn input"""
        return True

    @property
    def support_dzn(self):
        u"""Whether the solver supports dzn output"""
        return True

    @property
    def support_json(self):
        u"""Whether the solver supports json output"""
        return False

    @property
    def support_item(self):
        u"""Whether the solver supports item output"""
        return True

    @property
    def support_dict(self):
        u"""Whether the solver supports dict output"""
        return False

    @property
    def support_all(self):
        u"""Whether the solver supports collecting all solutions"""
        return True

    @property
    def support_timeout(self):
        u"""Whether the solver supports a timeout"""
        return True

    def solve(self, mzn_file, *dzn_files, **kwargs):
        if 'seed' in kwargs: seed = kwargs['seed']; del kwargs['seed']
        else: seed = 0
        if 'output_mode' in kwargs: output_mode = kwargs['output_mode']; del kwargs['output_mode']
        else: output_mode = u'item'
        if 'all_solutions' in kwargs: all_solutions = kwargs['all_solutions']; del kwargs['all_solutions']
        else: all_solutions = False
        if 'timeout' in kwargs: timeout = kwargs['timeout']; del kwargs['timeout']
        else: timeout = None
        if 'include' in kwargs: include = kwargs['include']; del kwargs['include']
        else: include = None
        if 'data' in kwargs: data = kwargs['data']; del kwargs['data']
        else: data = None
        u"""Solve a MiniZinc/FlatZinc problem with Chuffed.

        Parameters
        ----------
        mzn_file : str
            The path to the mzn file to solve.
        dzn_files
            A list of paths to dzn files.
        data : str
            A dzn string containing additional inline data to pass to the solver.
        include : str or [str]
            A path or a list of paths to included files.
        timeout : int
            The timeout for the solver. If None, no timeout given.
        all_solutions : bool
            Whether to return all solutions.
        output_mode : 'dzn', 'json', 'item', 'dict'
            The output mode required.
        seed : int
            Random seed.
        Returns
        -------
        str
            The output of the solver.
        """
        log = logging.getLogger(__name__)

        mzn = False
        args = []
        if mzn_file.endswith(u'fzn'):
            if output_mode != u'dzn':
                raise ValueError(u'Only dzn output available with fzn input.')
            args.append(self.fzn_cmd)
        else:
            if output_mode != u'item':
                raise ValueError(u'Only item output available with mzn input.')
            mzn = True
            args.append(self.mzn_cmd)
            args.append(u'-G')
            args.append(self.globals_dir)
            if include:
                if isinstance(include, unicode):
                    include = [include]
                for path in include:
                    args.append(u'-I')
                    args.append(path)
            if data:
                args.append(u'-D')
                args.append(data)

        fzn_flags = []
        if all_solutions:
            args.append(u'-a')
        if timeout and timeout > 0:
            fzn_flags.append(u'--time-out')
            fzn_flags.append(unicode(timeout)) # Gecode takes milliseconds
        if seed != 0:
            fzn_flags.append(u'--rnd-seed')
            fzn_flags.append(unicode(seed))
        if mzn and fzn_flags:
            args.append(u'--fzn-flags')
            args.append(u'"{}"'.format(u' '.join(fzn_flags)))
        else:
            args += fzn_flags
        args.append(mzn_file)
        if mzn and dzn_files:
            for dzn_file in dzn_files:
                args.append(dzn_file)

        try:
            process = run(args)
            out = process.stdout
            if process.stderr:
                raise RuntimeError(process.stderr)
        except CalledProcessError, err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr)
        return out


class Optimathsat(Solver):
    u"""Interface to the Optimathsat solver.

    Parameters
    ----------
    path : str
        The path to the optimathsat executable.
    globals_dir : str
        The path to the directory for global included files.
    """
    def __init__(self, path=u'optimathsat', globals_dir=u'std'):
        super(Optimathsat, self).__init__(globals_dir)
        self.cmd = path
        self._line_comm_p = re.compile(u'%.*\n')
        self._rational_p = re.compile(u'(\d+)\/(\d+)')

    @property
    def support_mzn(self):
        u"""Whether the solver supports direct mzn input"""
        return False

    @property
    def support_dzn(self):
        u"""Whether the solver supports dzn output"""
        return True

    @property
    def support_json(self):
        u"""Whether the solver supports json output"""
        return False

    @property
    def support_item(self):
        u"""Whether the solver supports item output"""
        return False

    @property
    def support_dict(self):
        u"""Whether the solver supports dict output"""
        return False

    @property
    def support_all(self):
        u"""Whether the solver supports collecting all solutions"""
        return False

    @property
    def support_timeout(self):
        u"""Whether the solver supports a timeout"""
        return False

    def _parse_out(self, out):
        out = self._line_comm_p.sub(out, u'')
        for m in self._rational_p.finditer(out):
            n, d = m.groups()
            val = float(n) / float(d)
            out = re.sub(u'{}/{}'.format(n, d), unicode(val), out)
        return out

    def solve(self, mzn_file, *dzn_files, **kwargs):
        if 'output_mode' in kwargs: output_mode = kwargs['output_mode']; del kwargs['output_mode']
        else: output_mode = u'item'
        if 'all_solutions' in kwargs: all_solutions = kwargs['all_solutions']; del kwargs['all_solutions']
        else: all_solutions = False
        if 'timeout' in kwargs: timeout = kwargs['timeout']; del kwargs['timeout']
        else: timeout = None
        if 'include' in kwargs: include = kwargs['include']; del kwargs['include']
        else: include = None
        if 'data' in kwargs: data = kwargs['data']; del kwargs['data']
        else: data = None
        u"""Solve a MiniZinc/FlatZinc problem with Optimathsat.

        Parameters
        ----------
        mzn_file : str
            The path to the fzn file to solve.
        Returns
        -------
        str
            The output of the solver in dzn format.
        """
        log = logging.getLogger(__name__)

        args = [self.cmd, u'-input=fzn', mzn_file]
        try:
            process = run(args)
            out = process.stdout
        except CalledProcessError, err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr)

        return self._parse_out(out)


class Opturion(Solver):
    u"""Interface to the Opturion CPX solver.

    Parameters
    ----------
    path : str
        The path to the fzn-cpx executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, path=u'fzn-cpx', globals_dir=u'opturion-cpx'):
        super(Opturion, self).__init__(globals_dir)
        self.cmd = path

    @property
    def support_mzn(self):
        u"""Whether the solver supports direct mzn input"""
        return False

    @property
    def support_dzn(self):
        u"""Whether the solver supports dzn output"""
        return True

    @property
    def support_json(self):
        u"""Whether the solver supports json output"""
        return False

    @property
    def support_item(self):
        u"""Whether the solver supports item output"""
        return False

    @property
    def support_dict(self):
        u"""Whether the solver supports dict output"""
        return False

    @property
    def support_all(self):
        u"""Whether the solver supports collecting all solutions"""
        return True

    @property
    def support_timeout(self):
        u"""Whether the solver supports a timeout"""
        return False

    def solve(self, mzn_file, *dzn_files, **kwargs):
        if 'output_mode' in kwargs: output_mode = kwargs['output_mode']; del kwargs['output_mode']
        else: output_mode = u'item'
        if 'all_solutions' in kwargs: all_solutions = kwargs['all_solutions']; del kwargs['all_solutions']
        else: all_solutions = False
        if 'timeout' in kwargs: timeout = kwargs['timeout']; del kwargs['timeout']
        else: timeout = None
        if 'include' in kwargs: include = kwargs['include']; del kwargs['include']
        else: include = None
        if 'data' in kwargs: data = kwargs['data']; del kwargs['data']
        else: data = None
        u"""Solve a MiniZinc/FlatZinc problem with Opturion CPX.

        Parameters
        ----------
        mzn_file : str
            The path to the fzn file to solve.
        Returns
        -------
        str
            The output of the solver in dzn format.
        """
        log = logging.getLogger(__name__)

        args = [self.cmd]
        if all_solutions:
            args.append(u'-a')
        args.append(mzn_file)

        try:
            process = run(args)
            out = process.stdout
        except CalledProcessError, err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr)

        return out


class MIPSolver(Solver):
    u"""Interface to the MIP solver.

    Parameters
    ----------
    path : str
        The path to the mzn-gurobi executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, path=u'mzn-gurobi', globals_dir=u'linear'):
        super(MIPSolver, self).__init__(globals_dir)
        self.cmd = path

    @property
    def support_mzn(self):
        u"""Whether the solver supports direct mzn input"""
        return True

    @property
    def support_dzn(self):
        u"""Whether the solver supports dzn output"""
        return True

    @property
    def support_json(self):
        u"""Whether the solver supports json output"""
        return True

    @property
    def support_item(self):
        u"""Whether the solver supports item output"""
        return True

    @property
    def support_dict(self):
        u"""Whether the solver supports dict output"""
        return False

    @property
    def support_all(self):
        u"""Whether the solver supports collecting all solutions"""
        return True

    @property
    def support_timeout(self):
        u"""Whether the solver supports a timeout"""
        return True

    def solve(self, mzn_file, *dzn_files, **kwargs):
        if 'parallel' in kwargs: parallel = kwargs['parallel']; del kwargs['parallel']
        else: parallel = 1
        if 'output_mode' in kwargs: output_mode = kwargs['output_mode']; del kwargs['output_mode']
        else: output_mode = u'item'
        if 'all_solutions' in kwargs: all_solutions = kwargs['all_solutions']; del kwargs['all_solutions']
        else: all_solutions = False
        if 'timeout' in kwargs: timeout = kwargs['timeout']; del kwargs['timeout']
        else: timeout = None
        if 'include' in kwargs: include = kwargs['include']; del kwargs['include']
        else: include = None
        if 'data' in kwargs: data = kwargs['data']; del kwargs['data']
        else: data = None
        u"""Solve a MiniZinc/FlatZinc problem with a MIP Solver.

        Parameters
        ----------
        mzn_file : str
            The path to the mzn file to solve.
        dzn_files
            A list of paths to dzn files.
        data : str
            A dzn string containing additional inline data to pass to the solver.
        include : str or [str]
            A path or a list of paths to included files.
        timeout : int
            The timeout for the solver. If None, no timeout given.
        all_solutions : bool
            Whether to return all solutions.
        output_mode : 'dzn', 'json', 'item', 'dict'
            The output mode required.
        parallel : int
            The number of threads to use to solve the problem; default is 1.
        Returns
        -------
        str
            The output of the solver.
        """
        log = logging.getLogger(__name__)

        mzn = False
        args = [self.cmd]
        if mzn_file.endswith(u'fzn') and output_mode not in [u'dzn', u'json']:
            raise ValueError(u'Only dzn or json output available with fzn input.')
        else:
            mzn = True
            args.append(u'-G')
            args.append(self.globals_dir)
            if include:
                if isinstance(include, unicode):
                    include = [include]
                for path in include:
                    args.append(u'-I')
                    args.append(path)
            if data:
                args.append(u'-D')
                args.append(data)

        if all_solutions:
            args.append(u'-a')
            args.append(u'--unique')
        if parallel != 1:
            args.append(u'-p')
            args.append(unicode(parallel))
        if timeout and timeout > 0:
            args.append(u'--timeout')
            args.append(unicode(timeout)) # Gurobi takes seconds

        args.append(u'--output-mode')
        args.append(output_mode)
        args.append(mzn_file)
        if mzn and dzn_files:
            for dzn_file in dzn_files:
                args.append(dzn_file)

        try:
            process = run(args)
            out = process.stdout
            print out
        except CalledProcessError, err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr)
        return out


class Gurobi(MIPSolver):
    u"""Interface to the Gurobi solver.

    Parameters
    ----------
    path : str
        The path to the mzn-cbc executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, path=u'mzn-gurobi', globals_dir=u'linear'):
        super(Gurobi, self).__init__(path, globals_dir)


class CBC(MIPSolver):
    u"""Interface to the COIN-OR CBC solver.

    Parameters
    ----------
    path : str
        The path to the mzn-cbc executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, path=u'mzn-cbc', globals_dir=u'linear'):
        super(CBC, self).__init__(path, globals_dir)


class G12Solver(Solver):
    u"""Interface to a generic G12 solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn executable.
    fzn_path : str
        The path to the flatzinc executable.
    globals_dir : str
        The path to the directory for global included files.
    backend : str
        The backend code of the specific solver used.
    """

    def __init__(self, mzn_path=u'mzn-g12fd', fzn_path=u'flatzinc',
                 globals_dir=u'g12_fd', backend=None):
        super(G12Solver, self).__init__(globals_dir)
        self.fzn_cmd = fzn_path
        self.mzn_cmd = mzn_path
        self.backend = backend

    @property
    def support_mzn(self):
        u"""Whether the solver supports direct mzn input"""
        return True

    @property
    def support_dzn(self):
        u"""Whether the solver supports dzn output"""
        return True

    @property
    def support_json(self):
        u"""Whether the solver supports json output"""
        return False

    @property
    def support_item(self):
        u"""Whether the solver supports item output"""
        return True

    @property
    def support_dict(self):
        u"""Whether the solver supports dict output"""
        return False

    @property
    def support_all(self):
        u"""Whether the solver supports collecting all solutions"""
        return True

    @property
    def support_timeout(self):
        u"""Whether the solver supports a timeout"""
        return False

    def solve(self, mzn_file, *dzn_files, **kwargs):
        if 'output_mode' in kwargs: output_mode = kwargs['output_mode']; del kwargs['output_mode']
        else: output_mode = u'item'
        if 'all_solutions' in kwargs: all_solutions = kwargs['all_solutions']; del kwargs['all_solutions']
        else: all_solutions = False
        if 'timeout' in kwargs: timeout = kwargs['timeout']; del kwargs['timeout']
        else: timeout = None
        if 'include' in kwargs: include = kwargs['include']; del kwargs['include']
        else: include = None
        if 'data' in kwargs: data = kwargs['data']; del kwargs['data']
        else: data = None
        u"""Solve a MiniZinc/FlatZinc problem with the G12 solver.

        Parameters
        ----------
        mzn_file : str
            The path to the mzn file to solve.
        dzn_files
            A list of paths to dzn files.
        data : str
            A dzn string containing additional inline data to pass to the solver.
        include : str or [str]
            A path or a list of paths to included files.
        all_solutions : bool
            Whether to return all solutions.
        output_mode : 'dzn', 'json', 'item', 'dict'
            The output mode required.
        Returns
        -------
        str
            The output of the solver.
        """
        log = logging.getLogger(__name__)

        mzn = False
        args = []
        if mzn_file.endswith(u'fzn'):
            if output_mode != u'dzn':
                raise ValueError(u'Only dzn output available with fzn input.')
            args.append(self.fzn_cmd)
            if self.backend:
                args.append(u'-b')
                args.append(self.backend)
        else:
            if output_mode != u'item':
                raise ValueError(u'Only item output available with mzn input.')
            mzn = True
            args.append(self.mzn_cmd)
            args.append(u'-G')
            args.append(self.globals_dir)
            if include:
                if isinstance(include, unicode):
                    include = [include]
                for path in include:
                    args.append(u'-I')
                    args.append(path)
            if data:
                args.append(u'-D')
                args.append(data)

        if all_solutions:
            args.append(u'-a')
        args.append(mzn_file)
        if mzn and dzn_files:
            for dzn_file in dzn_files:
                args.append(dzn_file)

        try:
            process = run(args)
            out = process.stdout
        except CalledProcessError, err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr)
        return out


class G12Fd(G12Solver):
    u"""Interface to the G12Fd solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn executable.
    fzn_path : str
        The path to the flatzinc executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, mzn_path=u'mzn-g12fd', fzn_path=u'flatzinc',
                 globals_dir=u'g12_fd'):
        super(G12Fd, self).__init__(mzn_path, fzn_path, globals_dir)


class G12Lazy(G12Solver):
    u"""Interface to the G12Lazy solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn executable.
    fzn_path : str
        The path to the flatzinc executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, mzn_path=u'mzn-g12lazy', fzn_path=u'flatzinc',
                 globals_dir=u'g12_lazyfd'):
        super(G12Lazy, self).__init__(mzn_path, fzn_path, globals_dir, u'lazy')


class G12MIP(G12Solver):
    u"""Interface to the G12MIP solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn executable.
    fzn_path : str
        The path to the flatzinc executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, mzn_path=u'mzn-g12mip', fzn_path=u'flatzinc',
                 globals_dir=u'linear'):
        super(G12MIP, self).__init__(mzn_path, fzn_path, globals_dir, u'mip')


#: Default Gecode instance.
gecode = Gecode()

#: Default Chuffed instance.
chuffed = Chuffed()

#: Default Optimathsat instance.
optimathsat = Optimathsat()

#: Default Opturion instance.
opturion = Opturion()

#: Default Gurobi instance.
gurobi = Gurobi()

#: Default CBC instance.
cbc = CBC()

#: Default G12Fd instance.
g12fd = G12Fd()

#: Default G12Lazy instance.
g12lazy = G12Lazy()

#: Default G12Lazy instance.
g12mip = G12MIP()

