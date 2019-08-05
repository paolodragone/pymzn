# -*- coding: utf-8 -*-
"""\
PyMzn interfaces with solvers through the ``Solver`` base class. This class
includes the necessary infomation for PyMzn to setup the solver, and provides
two main functions to support custom solver arguments and parsing the solution
stream of the solver.

PyMzn provides a number of solver implementations out-of-the-box.  PyMzn's
default solver is ``pymzn.gecode``, an instance of ``pymzn.Gecode``.

To use a solver that is not provided by PyMzn or to extend an existing one, one
has to subclass the ``Solver`` class and implement the ``args`` method, which
returns a list of command line arguments for executing the process. The
command line arguments supported by this function have to be paired with proper
``extraFlags`` in the solver configuration file (see the `solver configuration
files page
<https://www.minizinc.org/doc-latest/en/fzn-spec.html#solver-configuration-files>`__
from the MiniZinc reference manual for additional details).

For instance, suppose you have the following configuration file for an external
solver, ``my_solver.msc``:

.. code-block:: json

    {
      "name" : "My Solver",
      "version": "1.0",
      "id": "org.myorg.my_solver",
      "executable": "fzn-mysolver"
    }

You want to support the command line argument ``--solve-twice-as-fast``. First
you need to add the flag into the solver configuration file:

.. code-block:: json

    {
      "name" : "My Solver",
      "version": "1.0",
      "id": "org.myorg.my_solver",
      "executable": "fzn-mysolver",
      "extraFlags": [
          ["--solve-twice-as-fast", "provides twofold speedup", "bool", "false"]
      ]
    }

This will make the argument available to the ``minizinc`` executable when using
the solver ``my_solver``. Next, to add this option to PyMzn, you need to
subclass the ``Solver`` class and override the ``args`` function:

.. code-block:: python3
   :linenos:

    from pymzn import Solver

    class MySolver(Solver):
        def __init__(self):
            super().__init__(solver_id='my_solver')

        def args(self, solve_twice_as_fast=False, **kwargs):
            args = super().args(**kwargs)
            if solve_twice_as_fast:
                args.append('--solve-twice-as-fast')
            return args

It is then possible to run the ``minizinc`` function with the custom solver:

.. code-block:: python3

    my_solver = MySolver()
    pymzn.minizinc('test.mzn', solver=my_solver, solve_twice_as_fast=True)

"""

import re


__all__ = [
    'Solver', 'Gecode', 'Chuffed', 'Optimathsat', 'Opturion', 'MIPSolver',
    'Gurobi', 'CBC', 'OscarCBLS', 'ORTools', 'gecode', 'chuffed', 'optimathsat',
    'opturion', 'gurobi', 'cbc', 'oscar_cbls', 'or_tools'
]


class Solver:
    """Abstract solver class.

    Parameters
    ----------
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

        If the solver parser is able to parse statistics, this function should
        always add options to display statistics.

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
            args += ['-n', str(num_solutions)]
        if free_search:
            args.append('-f')
        if parallel is not None:
            args += ['-p', str(parallel)]
        if seed is not None:
            args += ['-r', str(seed)]
        return args

    class Parser:

        _line_comm_p = re.compile('%.*')

        def __init__(self):
            self._log = []

        @property
        def log(self):
            return '\n'.join(self._log)

        def parse_out(self):
            """Parse the output stream of the solver.

            This function is a generator that will receive in input the lines of
            the stdout of the minizinc solver via the send() function. For each
            line in input there should be a line in output.  This function
            should remove all the lines that are not part of the solution stream
            by yielding empty strings instead (which will be ignored by the
            solution parser).  This function should also process the lines
            following a non-standard dzn format, substituting them with
            equivalent standard dzn format (see e.g. Optimathsat).  Statistics
            should also be extracted, depending on the format of the solver, and
            then returned by the stats property.  Debug messages may be logged
            through the pymzn logger.
            """
            line = yield
            while True:
                if self._line_comm_p.match(line):
                    self._log.append(line)
                    line = yield ''
                else:
                    line = yield line

    def parser(self):
        """This function should return a new instance of the solver parser."""
        return Solver.Parser()


class Gecode(Solver):
    """Interface to the Gecode solver."""

    def __init__(self, solver_id='gecode'):
        super().__init__(solver_id)

    def args(self, fzn_flags=None, **kwargs):
        args = super().args(**kwargs)

        if fzn_flags:
            if isinstance(fzn_flags, str):
                fzn_flags = [fzn_flags]
            elif not isinstance(fzn_file, list):
                raise TypeError('Unrecognized type for fzn_flags argument.')
            args += ['--fzn-flags', ''.join(fzn_flags)]

        return args


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
        args = []
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

