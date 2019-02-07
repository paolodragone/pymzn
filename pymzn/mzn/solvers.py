# -*- coding: utf-8 -*-
"""Provides classes to interface solvers with PyMzn.

PyMzn interfaces with solvers through the ``Solver`` base class. This class
includes the necessary infomation for PyMzn to setup the solver, together with
the ``solve`` method, which respectively take care of the running or
asynchronously starting a process that solves the MiniZinc/FlatZinc model. PyMzn
provides a number of solver implementations out-of-the-box.  PyMzn's default
solver is ``pymzn.gecode``, an instance of `pymzn.Gecode`.

To use a solver that is not provided by PyMzn or to exend an existing one, one
has to subclass the `Solver` class and implement the ``args`` method, which
returns a list of command line arguments for executing the process. This is
generally enough for most solvers, but you can also directly reimplement the
``solve`` method for extra flexibility.

For instance::

    from pymzn import Solver
    from pymzn.process import Process

    class MySolver(Solver):
        def __init__(self, path='path/to/solver', globals_dir='path/to/gobals'):
            super().__init__(globals_dir)
            self.cmd = path

        def args(self, fzn_file, *args, arg1=val1, arg2=val2, **kwargs):
            return [self.cmd, '-arg1', arg1, '-arg2', arg2, fzn_file]

Then it is possible to run the ``minizinc`` function with the custom solver::

    my_solver = MySolver()
    pymzn.minizinc('test.mzn', solver=my_solver, arg1=val1, arg2=val2)
"""

import re

from .. import config as config
from ..log import logger


__all__ = [
    'Solver', 'Gecode', 'Chuffed', 'Optimathsat', 'Opturion', 'MIPSolver',
    'Gurobi', 'CBC', 'OscarCBLS', 'ORTools', 'gecode', 'chuffed', 'optimathsat',
    'opturion', 'gurobi', 'cbc', 'oscar_cbls', 'or_tools'
]


class Solver:
    """Abstract solver class.

    Parameter
    ---------
    solver_id : str
        The identifier to use when launching the minizinc command.
    """
    def __init__(self, solver_id):
        self.solver_id = solver_id

    def args(
        self, all_solutions=False, num_solutions=None, free_search=False,
        parallel=None, seed=None, **kwargs
    ):
        """Returns a list of command line arguments for the specified options.

        In all cases, this function should add options to display statistics and
        log messages.

        Parameters
        ----------
        all_solutions : bool
            Whether all the solutions must be returned (default is False).
        num_solutions : int
            The maximum number of solutions to be returned (only used in
            satisfation problems).
        free_search : bool
            Whether the solver should be instructed to perform a free search.
        parallel : int
            The number of parallel threads the solver should use.
        seed : int
            The random number generator seed to pass to the solver.
        """
        args = ['-s', '-v']
        if all_solutions:
            args.append('-a')
        if num_solutions is not None:
            args += ['-n', num_solutions]
        if free_search:
            args.append('-f')
        if parallel is not None:
            args += ['-p', parallel]
        if seed is not None:
            args += ['-r', seed]
        return args

    class Parser:

        _line_comm_p = re.compile('%.*')

        def __init__(self):
            self._stats = []

        @property
        def stats(self):
            return ''.join(self._stats)

        def parse_out(self):
            """Parse the output stream of the solver.

            This function is a generator that will receive in input the lines of
            the stdout of the minizinc solver via the send() function. For each
            line in input there should be a line in output.  This function
            should remove all the lines that are not part of the solution stream
            by yielding empty strings instead (which will be ignored by the
            solution parser).  This function should also process the lines
            following a non-standard dzn format, substituting them with
            equivalent standard dzn format (see e.g.  Optimathsat).  Statistics
            should also be extracted, depending on the format of the solver, and
            then returned by the stats property.  Debug messages may be logged
            through the pymzn logger.
            """
            line = yield
            while True:
                if self._line_comm_p.match(line):
                    self._stats.append(line)
                    line = yield ''
                else:
                    line = yield line

    def parser(self):
        return Solver.Parser()


class Gecode(Solver):
    """Interface to the Gecode solver."""

    def __init__(self, solver_id='gecode'):
        super().__init__(solver_id)


class Chuffed(Solver):
    """Interface to the Chuffed solver."""

    def __init__(self, solver_id='chuffed'):
        super().__init__(solver_id)


class Optimathsat(Solver):
    """Interface to the Optimathsat solver."""

    def __init__(self, solver_id='optimathsat'):
        super().__init__(solver_id)

    def args(
        self, all_solutions=False, num_solutions=None, free_search=False,
        parallel=None, seed=None, **kwargs
    ):
        args = ['-input=fzn']
        return args

    class Parser(Solver.Parser):

        _rational_p = re.compile('(\d+)\/(\d+)')

        def parse_out(self):
            line = yield
            while True:
                if self._line_comm_p.match(line):
                    self._stats.append(line)
                    line = yield ''
                else:
                    for m in self._rational_p.finditer(line):
                        n, d = m.groups()
                        val = float(n) / float(d)
                        line = re.sub('{}/{}'.format(n, d), str(val), line)
                    line = yield line

    def parser(self):
        return Optimathsat.Parser()


class Opturion(Solver):
    """Interface to the Opturion CPX solver."""

    def __init__(self, solver_id='opturion'):
        super().__init__(solver_id)


class MIPSolver(Solver):
    """Generic interface to MIP solvers."""


class Gurobi(MIPSolver):
    """Interface to the Gurobi solver.

    Parameters
    ----------
    dll : str
        The string containing the dll of your gurobi installation.
    """

    def __init__(self, solver_id='gurobi', dll=None):
        super().__init__(solver_id)
        self.dll = dll

    def args(self, *args, **kwargs):
        args = super().args(*args, **kwargs)
        if self.dll is not None:
            args += ['--dll', self.dll]
        return args

    def args(
        self, all_solutions=False, num_solutions=None, free_search=False,
        parallel=None, seed=None, **kwargs
    ):
        args = ['-s', '-v']
        if all_solutions:
            args.append('-a')
        if num_solutions is not None:
            args += ['-n', num_solutions]
        if free_search:
            args.append('-f')
        if parallel is not None:
            args += ['-p', parallel]
        if self.dll is not None:
            args += ['--gurobi-dll', self.dll]
        return args


class CBC(MIPSolver):
    """Interface to the COIN-OR CBC solver."""

    def __init__(self, solver_id='osicbc'):
        super().__init__(solver_id)


class OscarCBLS(Solver):
    """Interface to the Oscar/CBLS solver."""

    def __init__(self, solver_id='oscar-cbls'):
        super().__init__(solver_id)


class ORTools(Solver):
    """Interface to the OR-tools solver.

    Parameters
    ----------
    path : str
        The path to the fzn-or-tools executable.
    globals_dir : str
        The path to the directory for global included files. You should either
        copy or link the 'share/minizinc_cp' folder from the or-tools
        distribution into the minizinc library directory (with name 'or-tools')
        or provide the full path here.
    """

    def __init__(self, solver_id='or-tools'):
        super().__init__(solver_id)


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

#: Default Oscar/CBLS instance.
oscar_cbls = OscarCBLS()

#: Default ORTools instance.
or_tools = ORTools()

