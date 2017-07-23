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

import pymzn.config as config

from pymzn.bin import run
from pymzn._utils import get_logger

from subprocess import CalledProcessError


class Solver(ABC):
    """Abstract solver class.

    All the solvers inherit from this base class.
    """

    @property
    def globals_dir(self):
        """Global included files directory in the standard library"""
        return 'std'

    @property
    @abc.abstractmethod
    def support_mzn(self):
        """Whether the solver supports direct mzn input"""

    @property
    @abc.abstractmethod
    def support_dzn(self):
        """Whether the solver supports dzn output"""

    @property
    @abc.abstractmethod
    def support_json(self):
        """Whether the solver supports json output"""

    @property
    @abc.abstractmethod
    def support_item(self):
        """Whether the solver supports item output"""

    @property
    @abc.abstractmethod
    def support_dict(self):
        """Whether the solver supports dict output"""

    @property
    @abc.abstractmethod
    def support_all(self):
        """Whether the solver supports collecting all solutions"""

    @property
    @abc.abstractmethod
    def support_timeout(self):
        """Whether the solver supports a timeout"""

    @abc.abstractmethod
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
    path : str
        The path to the Gecode executable. If None, ``fzn-gecode`` is used.
    """
    def __init__(self, mzn_path='mzn-gecode', fzn_path='fzn-gecode',
                 globals_dir='gecode'):
        self.mzn_cmd = mzn_path
        self.fzn_cmd = fzn_path
        self._globals_dir = globals_dir

    @property
    def globals_dir(self):
        return self._globals_dir

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

    @property
    @abc.abstractmethod
    def support_dict(self):
        """Whether the solver supports dict output"""

    @property
    @abc.abstractmethod
    def support_all(self):
        """Whether the solver supports collecting all solutions"""

    @property
    @abc.abstractmethod
    def support_timeout(self):
        """Whether the solver supports a timeout"""

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
        str or SolnsStream
            The output of the solver if output_mode in ['dzn', 'json', 'item']
            or a SolnsStream of evaluated solutions if output_mode == 'dict'.
        """
        log = get_logger(__name__)

        mzn = False
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
                args.append(dzn_files)

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
    """Simple wrapper for the OptiMathSat solver.

    This is a simple interface to OptiMathSat which only specifies the input
    format as a FlatZinc model, without providing any additional arguments.

    Parameters
    ----------
    path : str
        The path to the OptiMathSat executable. If None, ``optimathsat`` is used.
    """
    def __init__(self, path=None):
        super().__init__(False, False, globals_dir='std')
        self.cmd = path or 'optimathsat'

    def solve(self, fzn_file, *, all_solutions=False, check_complete=False,
              **kwargs):
        """Solves a problem with the OptiMathSat solver.

        Parameters
        ----------
        fzn_file : str
            The path to the fzn file to use as input of the solver.
        all_solutions : bool
            Ignored.
        check_complete : bool
            Ignored.
        """
        args = [self.cmd, '-input=fzn', fzn_file]

        log = get_logger(__name__)
        try:
            process = run(args)
            out = process.stdout
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err

        if check_complete:
            return out, True
        return out


class Opturion(Solver):
    """Interface to the Opturion CPX solver.

    Parameters
    ----------
    path : str
        The path to the Opturion executable. If None, ``fzn-cpx`` is used.
    """

    def __init__(self, path=None):
        super().__init__(True, True, globals_dir='opturion-cpx')
        self.cmd = path or 'fzn-cpx'

    def solve(self, fzn_file, *, all_solutions=False, check_complete=False,
              timeout=None, **kwargs):
        """Solves a problem with the Opturion CPX solver.

        Parameters
        ----------
        fzn_file : str
            The path to the fzn file to use as input of the solver.
        all_solutions : bool
            Whether to return all solutions.
        check_complete : bool
            Whether to return a second boolean value indicating if the search
            was completed successfully.
        timeout : int or float
            The time cutoff in seconds, after which the execution is truncated
            and the best solution so far is returned, 0 or None means no cutoff;
            default is None.

        Returns
        -------
        str or tuple
            A string containing the solution output stream of the execution of
            Opturion on the specified problem; it can be directly be given to
            the function solns2out to be evaluated. If ``check_complete=True``
            returns an additional boolean, checking whether the search was
            completed before the timeout.
        """
        args = [self.cmd]

        if timeout or all_solutions:
            args.append('-a')

        args.append(fzn_file)

        log = get_logger(__name__)

        try:
            process = run(args, timeout=timeout)
            complete = not process.expired
            out = process.stdout
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err

        if check_complete:
            return out, complete
        return out


class Gurobi(Solver):
    """Interface to the Gurobi solver.

    Parameters
    ----------
    path : str
        The path to the Gurobi executable. If None, ``mzn-gurobi`` is used.
    """

    def __init__(self, path=None):
        super().__init__(True, True, globals_dir='std')
        self.cmd = path or 'mzn-gurobi'

    def solve(self, fzn_file, *, all_solutions=False, check_complete=False,
              timeout=None, **kwargs):
        """Solves a problem with the Opturion Gurobi solver.

        Parameters
        ----------
        fzn_file : str
            The path to the fzn file to use as input of the solver.
        all_solutions : bool
            Whether to return all solutions.
        check_complete : bool
            Whether to return a second boolean value indicating if the search
            was completed successfully.
        timeout : int or float
            The time cutoff in seconds, after which the execution is truncated
            and the best solution so far is returned, 0 or None means no cutoff;
            default is None.

        Returns
        -------
        str or tuple
            A string containing the solution output stream of the execution of
            Opturion on the specified problem; it can be directly be given to
            the function solns2out to be evaluated. If ``check_complete=True``
            returns an additional boolean, checking whether the search was
            completed before the timeout.
        """
        args = [self.cmd]

        if timeout or all_solutions:
            args.append('-a')

        args.append(fzn_file)

        log = get_logger(__name__)

        try:
            process = run(args, timeout=timeout)
            complete = not process.expired
            out = process.stdout
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err

        if check_complete:
            return out, complete
        return out


#: Default Gecode instance.
gecode = Gecode(path=config.get('gecode'))

#: Default Optimathsat instance.
optimathsat = Optimathsat(path=config.get('optimathsat'))

#: Default Opturion instance.
opturion = Opturion(path=config.get('opturion'))

#: Default Gurobi instance.
gurobi = Opturion(path=config.get('gurobi'))

