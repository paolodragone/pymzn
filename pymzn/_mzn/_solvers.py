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


class Solver(object):
    """Abstract solver class.

    All solver classes inherit from this class and provide implementations for
    the ``solve`` method.

    Attributes
    ----------
    support_ozn : bool
        Whether the solver's output can be parsed by ``solns2out``.
    support_all : bool
        Whether the solver supports the output of all solutions.
    globals_dir : str
        The directory containing the solver-specific redefinitions of global
        constraints, used when calling ``mzn2fzn``. This should be the default
        for the solver. When None is provided (default) the ``std`` directory is
        used.
    """
    def __init__(self, support_ozn, support_all, globals_dir=None):
        self.support_ozn = support_ozn
        self.support_all = support_all
        self.globals_dir = globals_dir

    def solve(self, fzn_file, *, all_solutions=False,
              check_complete=False, **kwargs):
        """Solve a problem encoded in FlatZinc.

        This method should call an external solver, wait for the solution and
        provide the output of the solver. If the solver does not have a Python
        interface, the ``pymzn.bin`` module can be used to run external
        executables.

        If ``support_ozn`` is ``False``, the solver should directly provide
        solutions compliant to the PyMzn solution format. This means that the
        the implementation of this method should parse the output of the solver
        and return the solutions as dictionaries of variable assignments (see
        the ``eval_dzn`` method). In alternative the solutions should be
        returned in dzn format, so they can be evaluated by the ``eval_dzn``
        function.

        Parameters
        ----------
        fzn_file : str
            The path to the fzn file to use as input of the solver.
        all_solutions : bool
            Whether the solver should output all the solutions. If
            ``support_all=False`` then the implementation should ignore the
            value of this parameter.
        check_complete : bool
            Whether the solver should return a second boolean value indicating
            if the search was completed successfully.
        **kwargs
            Additional arguments for the solver provided through the
            ``pymzn.minizinc`` function.

        Returns
        -------
        str, list or tuple
            This method should return a string if the solver supports ozn
            parsing via ``solns2out``. The string simply contains the output of
            the solver.
            If the solver does not support the ozn parsing, then it should parse
            the solvers output by itself and thus return a list of solutions in
            PyMzn format (dictionaries of variable assignments, as in
            ``pymzn.eval_dzn``).

            In both cases, if ``check_complete=True`` then the method should
            return a tuple containing the above output and a second boolean
            indicating whether the search was completed successfully.
        """
        raise NotImplementedError()


class Gecode(Solver):
    """Interface to the Gecode MILP solver.

    Parameters
    ----------
    path : str
        The path to the Gecode executable. If None, ``fzn-gecode`` is used.
    """
    def __init__(self, path=None):
        super().__init__(True, True, globals_dir='gecode')
        self.cmd = path or 'fzn-gecode'

    def solve(self, fzn_file, *, check_complete=False, all_solutions=False,
              timeout=0, parallel=1, n_solns=-1, seed=0, restart=None,
              restart_base=None, restart_scale=None, suppress_segfault=False,
              **kwargs):
        """Solves a problem with the Gecode solver.

        Parameters
        ----------
        fzn_file : str
            The path to the fzn file to use as input of the solver.
        all_solutions : bool
            Whether the solver should output all the solutions. Equivalent to
            ``n_solns=0``.
        check_complete : bool
            Whether the solver should return a second boolean value indicating
            if the search was completed successfully.
        n_solns : int
            The number of solutions to output (0 = all, -1 = one/best);
            the default is -1.
        parallel : int
            The number of threads to use to solve the problem
            (0 = #processing units); default is 1.
        time : int or float
            The time cutoff in seconds, after which the execution is truncated
            and the best solution so far is returned, 0 means no time cutoff;
            default is 0.
        seed : int
            Random seed; default is 0.
        restart : str
            Restart sequence type; default is None.
        restart_base : str
            Base for geometric restart sequence; if None (default) the default
            value of Gecode is used, which is 1.5.
        restart_scale : str
            Scale factor for restart sequence; if None (default) the default
            value of Gecode is used, which is 250.
        suppress_segfault : bool
            Whether to accept or not a solution returned when a segmentation
            fault has happened (this is unfortunately necessary sometimes due to
            some bugs in Gecode).

        Returns
        -------
        str or tuple
            A string containing the solution output stream of the execution of
            Gecode on the specified problem; it can be directly be given to the
            function solns2out to be evaluated. If ``check_complete=True``
            returns an additional boolean, checking whether the search was
            completed before the timeout.
        """
        log = get_logger(__name__)

        args = [self.cmd]
        if n_solns > 0:
            args.append('-n')
            args.append(str(n_solns))
        elif n_solns == 0 or all_solutions:
            args.append('-a')
        if parallel != 1:
            args.append('-p')
            args.append(str(parallel))
        if timeout > 0:
            args.append('-time')
            args.append(str(timeout * 1000)) # Gecode takes milliseconds
        if seed != 0:
            args.append('-r')
            args.append(str(seed))
        if restart:
            args.append('-restart')
            args.append(str(restart))
        if restart_base:
            args.append('-restart-base')
            args.append(str(restart_base))
        if restart_scale:
            args.append('-restart-scale')
            args.append(str(restart_scale))
        args.append(fzn_file)

        try:
            process = run(args)
            if timeout > 0:
                process.timeout = timeout
                if process.time >= timeout:
                    complete = False
            out = process.stdout
        except CalledProcessError as err:
            if suppress_segfault:
                log.warning('Gecode returned error code {} (segmentation '
                            'fault) but a solution was found and returned '
                            '(suppress_segfault=True).'.format(err.returncode))
                out = err.stdout
                complete = False
            else:
                log.exception(err.stderr)
                raise RuntimeError(err.stderr) from err
        if check_complete:
            return out, complete
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

