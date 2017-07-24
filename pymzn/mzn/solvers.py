# -*- coding: utf-8 -*-
"""Provides classes to interface solvers with PyMzn.

PyMzn interfaces with solvers through the ``Solver`` class. This class includes
the necessary infomation for PyMzn to setup the solver. This class also include
the ``solve`` method which takes care of the actual solving of a FlatZinc model.
The solvers classes are subclasses of the ``Solver`` class, providing
implementations of the ``solve`` method.
PyMzn provides a number of solver implementations out-of-the-box.
PyMzn's default solver is Gecode, which class is `pymzn.Gecode` and the default
instance is ``pymzn.gecode``.

To use a different solver or to exend an existing one, one has to subclass the
Solver class and implement the ``solve`` method.

For instance:::

    from pymzn.bin import run
    from pymzn import Solver

    class MySolver(Solver):
        def __init__(self, path='/path/to/solver'):
            self.path = path
            support_ozn = True
            support_all = False
            super().__init__(support_ozn, support_all)

        def solve(self, fzn_file, *, all_solutions=False, check_complete=False,
                  arg1=def_val1, arg2=def_val2, **kwargs):
        args = [self.path, '-arg1', arg1, '-arg2', arg2, fzn_file]
        process = run(args)
        return process.stdout


Then one can run the ``minizinc`` function with the custom solver:::

    pymzn.minizinc('test.mzn', solver=MySolver(), arg1=val1, arg2=val2)
"""

import re
import logging

import pymzn.config as config

from pymzn.utils import run
from abc import ABC, abstractmethod
from subprocess import CalledProcessError


class Solver(ABC):
    """Abstract solver class.

    All the solvers inherit from this base class.

    Parameters
    ----------
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, globals_dir='std'):
        self.globals_dir = globals_dir

    @property
    @abstractmethod
    def support_mzn(self):
        """Whether the solver supports direct mzn input"""

    @property
    @abstractmethod
    def support_dzn(self):
        """Whether the solver supports dzn output"""

    @property
    @abstractmethod
    def support_json(self):
        """Whether the solver supports json output"""

    @property
    @abstractmethod
    def support_item(self):
        """Whether the solver supports item output"""

    @property
    @abstractmethod
    def support_dict(self):
        """Whether the solver supports dict output"""

    @property
    @abstractmethod
    def support_all(self):
        """Whether the solver supports collecting all solutions"""

    @property
    @abstractmethod
    def support_timeout(self):
        """Whether the solver supports a timeout"""

    @abstractmethod
    def solve(self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
              all_solutions=False, output_mode='dzn', **kwargs):
        """Solve a problem encoded with MiniZinc/FlatZinc.

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
    """Interface to the Gecode solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn-gecode executable.
    fzn_path : str
        The path to the fzn-gecode executable.
    globals_dir : str
        The path to the directory for global included files.
    """
    def __init__(self, mzn_path='mzn-gecode', fzn_path='fzn-gecode',
                 globals_dir='gecode'):
        super().__init__(globals_dir)
        self.mzn_cmd = mzn_path
        self.fzn_cmd = fzn_path

    @property
    def support_mzn(self):
        """Whether the solver supports direct mzn input"""
        return True

    @property
    def support_dzn(self):
        """Whether the solver supports dzn output"""
        return True

    @property
    def support_json(self):
        """Whether the solver supports json output"""
        return False

    @property
    def support_item(self):
        """Whether the solver supports item output"""
        return True

    @property
    def support_dict(self):
        """Whether the solver supports dict output"""
        return False

    @property
    def support_all(self):
        """Whether the solver supports collecting all solutions"""
        return True

    @property
    def support_timeout(self):
        """Whether the solver supports a timeout"""
        return True

    def solve(self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
              all_solutions=False, output_mode='item', parallel=1, seed=0,
              suppress_segfault=False, **kwargs):
        """Solve a MiniZinc/FlatZinc problem with Gecode.

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

        args = []
        if mzn_file.endswith('fzn'):
            if output_mode != 'dzn':
                raise ValueError('Only dzn output available with fzn input.')
            args.append(self.fzn_cmd)
        else:
            if output_mode != 'item':
                raise ValueError('Only item output available with mzn input.')
            mzn = True
            args.append(self.mzn_cmd)
            args.append('-G')
            args.append(self.globals_dir)
            if include:
                if isinstance(include, str):
                    include = [include]
                for path in include:
                    args.append('-I')
                    args.append(path)
            if data:
                args.append('-D')
                args.append(data)

        if all_solutions:
            args.append('-a')
        if parallel != 1:
            args.append('-p')
            args.append(str(parallel))
        if timeout and timeout > 0:
            args.append('-time')
            args.append(str(timeout * 1000)) # Gecode takes milliseconds
        if seed != 0:
            args.append('-r')
            args.append(str(seed))
        args.append(mzn_file)
        if mzn and dzn_files:
            for dzn_file in dzn_files:
                args.append(dzn_file)

        try:
            process = run(args)
            out = process.stdout
        except CalledProcessError as err:
            if suppress_segfault:
                log.warning('Gecode returned error code {} (segmentation '
                            'fault) but a solution was found and returned '
                            '(suppress_segfault=True).'.format(err.returncode))
                out = err.stdout
            else:
                log.exception(err.stderr)
                raise RuntimeError(err.stderr) from err
        return out


class Optimathsat(Solver):
    """Interface to the Optimathsat solver.

    Parameters
    ----------
    path : str
        The path to the optimathsat executable.
    globals_dir : str
        The path to the directory for global included files.
    """
    def __init__(self, path='optimathsat'):
        super().__init__()
        self.cmd = path
        self._line_comm_p = re.compile('%.*\n')
        self._rational_p = re.compile('(\d+)\/(\d+)')

    @property
    def support_mzn(self):
        """Whether the solver supports direct mzn input"""
        return False

    @property
    def support_dzn(self):
        """Whether the solver supports dzn output"""
        return True

    @property
    def support_json(self):
        """Whether the solver supports json output"""
        return False

    @property
    def support_item(self):
        """Whether the solver supports item output"""
        return False

    @property
    def support_dict(self):
        """Whether the solver supports dict output"""
        return False

    @property
    def support_all(self):
        """Whether the solver supports collecting all solutions"""
        return False

    @property
    def support_timeout(self):
        """Whether the solver supports a timeout"""
        return False

    def _parse_out(self, out):
        out = self._line_comm_p.sub(out, '')
        for m in self._rational_p.finditer(out):
            n, d = m.groups()
            val = float(n) / float(d)
            out = re.sub('{}/{}'.format(n, d), str(val), out)
        return out

    def solve(self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
              all_solutions=False, output_mode='item', **kwargs):
        """Solve a MiniZinc/FlatZinc problem with Optimathsat.

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

        args = [self.cmd, '-input=fzn', mzn_file]
        try:
            process = run(args)
            out = process.stdout
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err

        return self._parse_out(out)


class Opturion:
    """Interface to the Opturion CPX solver.

    Parameters
    ----------
    path : str
        The path to the fzn-cpx executable.
    """

    def __init__(self, path='fzn-cpx'):
        super().__init__()
        self.cmd = path

    @property
    def support_mzn(self):
        """Whether the solver supports direct mzn input"""
        return False

    @property
    def support_dzn(self):
        """Whether the solver supports dzn output"""
        return True

    @property
    def support_json(self):
        """Whether the solver supports json output"""
        return False

    @property
    def support_item(self):
        """Whether the solver supports item output"""
        return False

    @property
    def support_dict(self):
        """Whether the solver supports dict output"""
        return False

    @property
    def support_all(self):
        """Whether the solver supports collecting all solutions"""
        return True

    @property
    def support_timeout(self):
        """Whether the solver supports a timeout"""
        return False

    def solve(self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
              all_solutions=False, output_mode='item', **kwargs):
        """Solve a MiniZinc/FlatZinc problem with Opturion CPX.

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
            args.append('-a')
        args.append(mzn_file)

        try:
            process = run(args)
            out = process.stdout
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err

        return out


class Gurobi(Solver):
    """Interface to the Gurobi solver.

    Parameters
    ----------
    path : str
        The path to the mzn-gurobi executable.
    """

    def __init__(self, path='mzn-gurobi'):
        super().__init__()
        self.cmd = path

    @property
    def support_mzn(self):
        """Whether the solver supports direct mzn input"""
        return True

    @property
    def support_dzn(self):
        """Whether the solver supports dzn output"""
        return True

    @property
    def support_json(self):
        """Whether the solver supports json output"""
        return True

    @property
    def support_item(self):
        """Whether the solver supports item output"""
        return True

    @property
    def support_dict(self):
        """Whether the solver supports dict output"""
        return False

    @property
    def support_all(self):
        """Whether the solver supports collecting all solutions"""
        return True

    @property
    def support_timeout(self):
        """Whether the solver supports a timeout"""
        return True

    def solve(self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
              all_solutions=False, output_mode='item', parallel=1, **kwargs):
        """Solve a MiniZinc/FlatZinc problem with Gurobi.

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

        args = [self.cmd]
        if mzn_file.endswith('fzn') and output_mode not in ['dzn', 'json']:
            raise ValueError('Only dzn or json output available with fzn input.')
        else:
            if output_mode != 'item':
                raise ValueError('Only item output available with mzn input.')
            mzn = True
            if include:
                if isinstance(include, str):
                    include = [include]
                for path in include:
                    args.append('-I')
                    args.append(path)
            if data:
                args.append('-D')
                args.append(data)

        if all_solutions:
            args.append('-a')
            args.append('--unique')
        if parallel != 1:
            args.append('-p')
            args.append(str(parallel))
        if timeout and timeout > 0:
            args.append('-time')
            args.append(str(timeout)) # Gurobi takes seconds

        args.append('--output-mode')
        args.append(output_mode)
        args.append(mzn_file)
        if mzn and dzn_files:
            for dzn_file in dzn_files:
                args.append(dzn_file)

        try:
            process = run(args)
            out = process.stdout
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err
        return out


#: Default Gecode instance.
gecode = Gecode()

#: Default Optimathsat instance.
optimathsat = Optimathsat()

#: Default Opturion instance.
opturion = Opturion()

#: Default Gurobi instance.
gurobi = Gurobi()


