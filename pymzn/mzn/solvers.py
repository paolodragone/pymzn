# -*- coding: utf-8 -*-
"""Provides classes to interface solvers with PyMzn.

PyMzn interfaces with solvers through the ``Solver`` base class. This class
includes the necessary infomation for PyMzn to setup the solver, together with
the ``solve`` and ``solve_start`` methods, which respectively take care of the
running or asynchronously starting a process that solves the MiniZinc/FlatZinc
model. PyMzn provides a number of solver implementations out-of-the-box.
PyMzn's default solver is ``pymzn.gecode``, an instance of `pymzn.Gecode`.

To use a solver that is not provided by PyMzn or to exend an existing one, one
has to subclass the `Solver` class and implement the ``args`` method, which
returns a list of command line arguments for executing the process. This is
generally enough for most solvers, but you can also directly reimplement the
``solve`` and ``solve_start`` methods for extra flexibility.

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
import logging

import pymzn.config as config

from ..process import Process
from subprocess import CalledProcessError


class Solver:
    """Abstract solver class.

    All the solvers inherit from this base class.

    Parameters
    ----------
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(
        self, globals_dir='std', support_mzn=False, support_all=False,
        support_num=False, support_timeout=False, support_output_mode=False,
        support_stats=False
    ):
        self.globals_dir = globals_dir
        self.support_mzn = support_mzn
        self.support_all = support_all
        self.support_num = support_num
        self.support_timeout = support_timeout
        self.support_output_mode = support_output_mode
        self.support_stats = support_stats

    def args(*args, **kwargs):
        """Returns the command line arguments to start the solver"""
        raise NotImplementedError()

    def solve_start(self, *args, timeout=None, all_solutions=False, **kwargs):
        """Like `solve`, but returns a started Process"""
        log = logging.getLogger(__name__)

        if timeout and not self.support_timeout:
            if not self.support_all:
                raise ValueError('Timeout not supported')
            all_solutions = True

        solver_args = self.args(
            *args, timeout=timeout, all_solutions=all_solutions, **kwargs
        )
        timeout = None if self.support_timeout else timeout

        try:
            log.debug('Starting solver with arguments {}'.format(solver_args))
            return Process(solver_args).start(timeout=timeout)
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err

    def solve(self, *args, timeout=None, all_solutions=False, **kwargs):
        """Solve a problem encoded with MiniZinc/FlatZinc.

        This method should call an external solver, wait for the solution and
        provide the output of the solver. If the solver does not have a Python
        interface, the ``pymzn.process`` module can be used to run external
        executables.

        If a solver does not support dzn output, then its PyMzn implementation
        should take care of parsing the solver output and return a dzn
        equivalent.
        """
        log = logging.getLogger(__name__)

        if timeout and not self.support_timeout:
            if not self.support_all:
                raise ValueError('Timeout not supported')
            all_solutions = True

        solver_args = self.args(
            *args, timeout=timeout, all_solutions=all_solutions, **kwargs
        )
        timeout = None if self.support_timeout else timeout

        try:
            log.debug('Running solver with arguments {}'.format(solver_args))
            process = Process(solver_args).run(timeout=timeout)
            out = process.stdout_data
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err
        return out


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
    def __init__(
        self, mzn_path='mzn-gecode', fzn_path='fzn-gecode', globals_dir='gecode'
    ):
        super().__init__(
            globals_dir, support_mzn=True, support_all=True, support_num=True,
            support_timeout=True, support_stats=True
        )
        self.mzn_cmd = mzn_path
        self.fzn_cmd = fzn_path

    def args(
        self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
        all_solutions=False, num_solutions=None, output_mode='item', parallel=1,
        seed=0, statistics=False, **kwargs
    ):
        mzn = False
        args = []
        if mzn_file.endswith('fzn'):
            args.append(self.fzn_cmd)
        else:
            mzn = True
            args += [self.mzn_cmd, '-G', self.globals_dir]
            if include:
                if isinstance(include, str):
                    include = [include]
                for path in include:
                    args += ['-I', path]
            if data:
                args += ['-D', data]

        fzn_flags = []
        if statistics:
            args.append('-s')
        if all_solutions:
            args.append('-a')
        if num_solutions is not None:
            args += ['-n', str(num_solutions)]
        if parallel != 1:
            fzn_flags += ['-p', str(parallel)]
        if timeout and timeout > 0:
            timeout = timeout * 1000 # Gecode takes milliseconds
            fzn_flags += ['-time', str(timeout)]
        if seed != 0:
            fzn_flags += ['-r', str(seed)]
        if mzn and fzn_flags:
            args += ['--fzn-flags', '{}'.format(' '.join(fzn_flags))]
        else:
            args += fzn_flags

        args.append(mzn_file)
        if mzn and dzn_files:
            for dzn_file in dzn_files:
                args.append(dzn_file)
        return args

    def solve(self, *args, suppress_segfault=False, **kwargs):
        """Solve a MiniZinc/FlatZinc problem with Gecode.

        Parameters
        ----------
        suppress_segfault : bool
            Whether to accept or not a solution returned when a segmentation
            fault has happened (this is unfortunately necessary sometimes due to
            some bugs in Gecode).
        """
        log = logging.getLogger(__name__)

        solver_args = self.args(*args, **kwargs)

        try:
            log.debug('Running solver with arguments {}'.format(solver_args))
            process = Process(solver_args).run()
            out = process.stdout_data
        except CalledProcessError as err:
            if suppress_segfault and len(err.stdout) > 0 \
                    and err.stderr.startswith('Segmentation fault'):
                log.warning('Gecode returned error code {} (segmentation '
                            'fault) but a solution was found and returned '
                            '(suppress_segfault=True).'.format(err.returncode))
                out = err.stdout
            else:
                log.exception(err.stderr)
                raise RuntimeError(err.stderr) from err
        return out


class Chuffed(Solver):
    """Interface to the Chuffed solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn-chuffed executable.
    fzn_path : str
        The path to the fzn-chuffed executable.
    globals_dir : str
        The path to the directory for global included files.
    """
    def __init__(
        self, mzn_path='mzn-chuffed', fzn_path='fzn-chuffed',
        globals_dir='chuffed'
    ):
        super().__init__(
             globals_dir, support_mzn=True, support_all=True, support_num=True,
             support_timeout=True
        )
        self.mzn_cmd = mzn_path
        self.fzn_cmd = fzn_path

    def args(
        self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
        all_solutions=False, num_solutions=None, output_mode='item', seed=0,
        **kwargs
    ):
        mzn = False
        args = []
        if mzn_file.endswith('fzn'):
            args.append(self.fzn_cmd)
        else:
            mzn = True
            args += [self.mzn_cmd, '-G', self.globals_dir]
            if include:
                if isinstance(include, str):
                    include = [include]
                for path in include:
                    args += ['-I', path]
            if data:
                args += ['-D', data]

        fzn_flags = []
        if all_solutions:
            args.append('-a')
        if num_solutions is not None:
            args += ['-n', str(num_solutions)]
        if timeout and timeout > 0:
            fzn_flags += ['--time-out', str(timeout)]
        if seed != 0:
            fzn_flags += ['--rnd-seed', str(seed)]
        if mzn and fzn_flags:
            args += ['--fzn-flags', '"{}"'.format(' '.join(fzn_flags))]
        else:
            args += fzn_flags

        args.append(mzn_file)
        if mzn and dzn_files:
            for dzn_file in dzn_files:
                args.append(dzn_file)
        return args


class Optimathsat(Solver):
    """Interface to the Optimathsat solver.

    Parameters
    ----------
    path : str
        The path to the optimathsat executable.
    globals_dir : str
        The path to the directory for global included files.
    """
    def __init__(self, path='optimathsat', globals_dir='std'):
        super().__init__(globals_dir, support_stats=True)
        self.cmd = path
        self._line_comm_p = re.compile('%.*\n')
        self._rational_p = re.compile('(\d+)\/(\d+)')

    def _parse_out(self, out, statistics=False):
        stats = ''.join(self._line_comm_p.findall(out))
        out = self._line_comm_p.sub(out, '')
        for m in self._rational_p.finditer(out):
            n, d = m.groups()
            val = float(n) / float(d)
            out = re.sub('{}/{}'.format(n, d), str(val), out)
        if statistics:
            return '\n'.join([out, stats])
        return out

    def args(self, fzn_file, *args, **kwargs):
        return [self.cmd, '-input=fzn', fzn_file]

    def solve(fzn_file, *args, statistics=False, **kwargs):
        return self._parse_out(
            super().solve(fzn_file, *args, **kwargs), statistics
        )

    def solve_start(self, *args, **kwargs):
        raise NotImplementedError()


class Opturion(Solver):
    """Interface to the Opturion CPX solver.

    Parameters
    ----------
    path : str
        The path to the fzn-cpx executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, path='fzn-cpx', globals_dir='opturion-cpx'):
        super().__init__(globals_dir, support_all=True, support_stats=True)
        self.cmd = path

    def args(
        self, fzn_file, *args, all_solutions=False, statistics=False, **kwargs
    ):
        args = [self.cmd]
        if all_solutions:
            args.append('-a')
        if statistics:
            args.append('-s')
        args.append(fzn_file)
        return args


class MIPSolver(Solver):
    """Interface to the MIP solver.

    Parameters
    ----------
    path : str
        The path to the mzn-gurobi executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, path='mzn-gurobi', globals_dir='linear'):
        super().__init__(
            globals_dir, support_mzn=True, support_all=True, support_num=True,
            support_timeout=True, support_output_mode=True, support_stats=True
        )
        self.cmd = path

    def args(
        self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
        all_solutions=False, num_solutions=None, output_mode='item', parallel=1,
        statistics=False, **kwargs
    ):
        mzn = False
        args = [self.cmd]
        if mzn_file.endswith('fzn') and output_mode not in ['dzn', 'json']:
            raise ValueError('Only dzn or json output available with fzn input')
        else:
            mzn = True
            args += ['-G', self.globals_dir]
            if include:
                if isinstance(include, str):
                    include = [include]
                for path in include:
                    args += ['-I', path]
            if data:
                args += ['-D', data]

        if statistics:
            args.append('-s')
        if all_solutions:
            args += ['-a', '--unique']
        if num_solutions is not None:
            args += ['-n', str(num_solutions)]
        if parallel != 1:
            args += ['-p', str(parallel)]
        if timeout and timeout > 0:
            args += ['--timeout', str(timeout)]

        args += ['--output-mode', output_mode, mzn_file]
        if mzn and dzn_files:
            for dzn_file in dzn_files:
                args.append(dzn_file)
        return args


class Gurobi(MIPSolver):
    """Interface to the Gurobi solver.

    Parameters
    ----------
    path : str
        The path to the mzn-cbc executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, path='mzn-gurobi', globals_dir='linear'):
        super().__init__(path, globals_dir)


class CBC(MIPSolver):
    """Interface to the COIN-OR CBC solver.

    Parameters
    ----------
    path : str
        The path to the mzn-cbc executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(self, path='mzn-cbc', globals_dir='linear'):
        super().__init__(path, globals_dir)


class G12Solver(Solver):
    """Interface to a generic G12 solver.

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

    def __init__(
        self, mzn_path='mzn-g12fd', fzn_path='flatzinc', globals_dir='g12_fd',
        backend=None
    ):
        super().__init__(
            globals_dir, support_mzn=True, support_all=True, support_num=True,
            support_stats=True
        )
        self.fzn_cmd = fzn_path
        self.mzn_cmd = mzn_path
        self.backend = backend

    def args(
        self, mzn_file, *dzn_files, data=None, include=None, statistics=False,
        all_solutions=False, num_solutions=None, **kwargs
    ):
        mzn = False
        args = []
        if mzn_file.endswith('fzn'):
            args.append(self.fzn_cmd)
            if self.backend:
                args += ['-b', self.backend]
        else:
            mzn = True
            args += [self.mzn_cmd, '-G', self.globals_dir]
            if include:
                if isinstance(include, str):
                    include = [include]
                for path in include:
                    args += ['-I', path]
            if data:
                args += ['-D', data]

        if statistics:
            args.append('-s')
        if all_solutions:
            args.append('-a')
        if num_solutions is not None:
            args += ['-n', str(num_solutions)]
        args.append(mzn_file)
        if mzn and dzn_files:
            for dzn_file in dzn_files:
                args.append(dzn_file)
        return args


class G12Fd(G12Solver):
    """Interface to the G12Fd solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn executable.
    fzn_path : str
        The path to the flatzinc executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(
        self, mzn_path='mzn-g12fd', fzn_path='flatzinc', globals_dir='g12_fd'
    ):
        super().__init__(mzn_path, fzn_path, globals_dir)


class G12Lazy(G12Solver):
    """Interface to the G12Lazy solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn executable.
    fzn_path : str
        The path to the flatzinc executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(
        self, mzn_path='mzn-g12lazy', fzn_path='flatzinc',
        globals_dir='g12_lazyfd'
    ):
        super().__init__(mzn_path, fzn_path, globals_dir, 'lazy')


class G12MIP(G12Solver):
    """Interface to the G12MIP solver.

    Parameters
    ----------
    mzn_path : str
        The path to the mzn executable.
    fzn_path : str
        The path to the flatzinc executable.
    globals_dir : str
        The path to the directory for global included files.
    """

    def __init__(
        self, mzn_path='mzn-g12mip', fzn_path='flatzinc', globals_dir='linear'
    ):
        super().__init__(mzn_path, fzn_path, globals_dir, 'mip')


class OscarCBLS(Solver):
    """Interface to the Oscar/CBLS solver.

    Parameters
    ----------
    path : str
        The path to the fzn-oscar-cbls executable.
    globals_dir : str
        The path to the directory for global included files.  You should either
        copy or link the 'mznlib' folder from the oscar-cbls-flatzinc
        distribution into the minizinc library directory.
    """

    def __init__(self, path='fzn-oscar-cbls', globals_dir='oscar-cbls'):
        super().__init__(
            globals_dir, support_all=True, support_num=True,
            support_timeout=True, support_stats=True
        )
        self.cmd = path

    def args(
        self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
        all_solutions=False, num_solutions=None, statistics=False, **kwargs
    ):
        """Solve a FlatZinc problem with Oscar/CBLS.

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
        if statistics:
            args += ['-s', '-v']
        if all_solutions:
            args.append('-a')
        if num_solutions is not None:
            args += ['-n', str(num_solutions)]
        if timeout:
            args += ['-t', str(timeout)]
        args.append(mzn_file)
        return args

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

#: Default Oscar/CBLS instance.
oscar_cbls = OscarCBLS()

