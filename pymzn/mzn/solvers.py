# -*- coding: utf-8 -*-
"""Provides classes to interface solvers with PyMzn.

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
        def __init__(self, path='path/to/solver', globals_dir='path/to/gobals'):
            super().__init__(globals_dir, support_mzn=False, support_dzn=True,
                 support_json=False, support_item=False, support_dict=False,
                 support_all=False, support_timeout=False)
            self.cmd = path

        \"\"\"
        You can ignore the dzn_files, data and include if the solver does not
        support mzn inputs. Similarly, you can ignore timeout and
        all_solutions if the solver does not support the timeout and returning
        all solutions respectively. Check out the Gecode implementation for
        an example of how to handle these parameters if needed.
        \"\"\"
        def solve(self, mzn_file, *dzn_files, data=None, include=None,
                  timeout=None, all_solutions=False, output_mode='dzn',
                  arg1=def_val1, arg2=def_val2, **kwargs):
        # mzn_file contains a fzn if the solver does not support mzn inputs
        args = [self.path, '-arg1', arg1, '-arg2', arg2, mzn_file]
        process = run(args)
        return process.stdout    # assuming the solver returns dzn solutions


Then one can run the ``minizinc`` function with the custom solver::

    my_solver = MySolver()
    pymzn.minizinc('test.mzn', solver=my_solver, arg1=val1, arg2=val2)
"""

import re
import os
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

    def __init__(self, globals_dir='std', support_mzn=False, support_dzn=True,
                 support_json=False, support_item=False, support_dict=False,
                 support_all=False, support_timeout=False):
        self.globals_dir = globals_dir
        self.support_mzn = support_mzn
        self.support_dzn = support_dzn
        self.support_json = support_json
        self.support_item = support_item
        self.support_dict = support_dict
        self.support_all = support_all
        self.support_timeout = support_timeout

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
        super().__init__(globals_dir, support_mzn=True, support_dzn=True,
                support_json=False, support_item=True, support_dict=False,
                support_all=True, support_timeout=True)
        self.mzn_cmd = mzn_path
        self.fzn_cmd = fzn_path

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

        try:
            process = run(args)
            out = process.stdout
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
    def __init__(self, mzn_path='mzn-chuffed', fzn_path='fzn-chuffed',
                 globals_dir='chuffed'):
        super().__init__(globals_dir, support_mzn=True, support_dzn=True,
                support_json=False, support_item=True, support_dict=False,
                support_all=True, support_timeout=True)
        self.mzn_cmd = mzn_path
        self.fzn_cmd = fzn_path

    def solve(self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
              all_solutions=False, output_mode='item', seed=0, **kwargs):
        """Solve a MiniZinc/FlatZinc problem with Chuffed.

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
        if mzn_file.endswith('fzn'):
            if output_mode != 'dzn':
                raise ValueError('Only dzn output available with fzn input.')
            args.append(self.fzn_cmd)
        else:
            if output_mode != 'item':
                raise ValueError('Only item output available with mzn input.')
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

        try:
            process = run(args)
            out = process.stdout
            if process.stderr:
                raise RuntimeError(process.stderr)
        except CalledProcessError as err:
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
    def __init__(self, path='optimathsat', globals_dir='std'):
        super().__init__(globals_dir, support_mzn=False, support_dzn=True,
                support_json=False, support_item=False, support_dict=False,
                support_all=False, support_timeout=False)
        self.cmd = path
        self._line_comm_p = re.compile('%.*\n')
        self._rational_p = re.compile('(\d+)\/(\d+)')

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
        super().__init__(globals_dir, support_mzn=False, support_dzn=True,
                support_json=False, support_item=False, support_dict=False,
                support_all=True, support_timeout=False)
        self.cmd = path

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
        super().__init__(globals_dir, support_mzn=True, support_dzn=True,
                support_json=True, support_item=True, support_dict=False,
                support_all=True, support_timeout=True)
        self.cmd = path

    def solve(self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
              all_solutions=False, output_mode='item', parallel=1, **kwargs):
        """Solve a MiniZinc/FlatZinc problem with a MIP Solver.

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
        if mzn_file.endswith('fzn') and output_mode not in ['dzn', 'json']:
            raise ValueError('Only dzn or json output available with fzn input.')
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

        if all_solutions:
            args += ['-a', '--unique']
        if parallel != 1:
            args += ['-p', str(parallel)]
        if timeout and timeout > 0:
            args += ['--timeout', str(timeout)]

        args += ['--output-mode', output_mode, mzn_file]
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

    def __init__(self, mzn_path='mzn-g12fd', fzn_path='flatzinc',
                 globals_dir='g12_fd', backend=None):
        super().__init__(globals_dir, support_mzn=True, support_dzn=True,
                support_json=False, support_item=True, support_dict=False,
                support_all=True, support_timeout=False)
        self.fzn_cmd = fzn_path
        self.mzn_cmd = mzn_path
        self.backend = backend

    def solve(self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
              all_solutions=False, output_mode='item', **kwargs):
        """Solve a MiniZinc/FlatZinc problem with the G12 solver.

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
        if mzn_file.endswith('fzn'):
            if output_mode != 'dzn':
                raise ValueError('Only dzn output available with fzn input.')
            args.append(self.fzn_cmd)
            if self.backend:
                args += ['-b', self.backend]
        else:
            if output_mode != 'item':
                raise ValueError('Only item output available with mzn input.')
            mzn = True
            args += [self.mzn_cmd, '-G', self.globals_dir]
            if include:
                if isinstance(include, str):
                    include = [include]
                for path in include:
                    args += ['-I', path]
            if data:
                args += ['-D', data]

        if all_solutions:
            args.append('-a')
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

    def __init__(self, mzn_path='mzn-g12fd', fzn_path='flatzinc',
                 globals_dir='g12_fd'):
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

    def __init__(self, mzn_path='mzn-g12lazy', fzn_path='flatzinc',
                 globals_dir='g12_lazyfd'):
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

    def __init__(self, mzn_path='mzn-g12mip', fzn_path='flatzinc',
                 globals_dir='linear'):
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
        super().__init__(globals_dir, support_mzn=False, support_dzn=True,
                support_json=False, support_item=False, support_dict=False,
                support_all=True, support_timeout=True)
        self.cmd = path

    def solve(self, mzn_file, *dzn_files, data=None, include=None, timeout=None,
              all_solutions=False, output_mode='item', **kwargs):
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
        if all_solutions:
            args.append('-a')
        if timeout:
            args += ['-t', str(timeout)]
        args.append(mzn_file)

        try:
            process = run(args)
            out = process.stdout
        except CalledProcessError as err:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err

        return out

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

