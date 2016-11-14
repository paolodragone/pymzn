"""
PyMzn interfaces with solvers through *proxy* functions. Proxy functions
executes a solver with the given arguments on the provided FlatZinc model.
PyMzn's default solver is Gecode, which proxy function is `pymzn.gecode`.

If you want to use a different solver other than Gecode, you first need
to make sure that it supports the FlatZinc input format, then you need to find
an appropriate proxy function if it exists, otherwise you can implement one by
yourself. PyMzn provides natively a number of solvers proxy functions.
If the solver your solver is not supported natively, you can use the
generic proxy function ``pymzn.solve``:

::

    pymzn.minizinc('test.mzn', fzn_fn=pymzn.solve, solver_cmd='path/to/solver')

If you want to provide additional arguments and flexibility to the
solver, you can define your own proxy function. Here is an example:

::

    from pymzn.binary import cmd, run

    def my_solver(fzn_file, arg1=def_val1, arg2=def_val2):
        solver = 'path/to/solver'
        args = [('-arg1', arg1), ('-arg2', arg2), fzn_file]
        return run(cmd(solver, args))

Then you can run the ``minizinc`` function like this:

::

    pymzn.minizinc('test.mzn', fzn_cmd=fzn_solver, arg1=val1, arg2=val2)

"""
import pymzn.config as config

from pymzn.bin import run
from pymzn._utils import get_logger

from subprocess import CalledProcessError


class Solver(object):

    def __init__(self, support_ozn, globals_dir=None):
        self.support_ozn = support_ozn
        self.globals_dir = globals_dir

    def solve(self, fzn_file, *args, check_complete=False, **kwargs):
        raise NotImplementedError()


class Gecode(Solver):

    def __init__(self, path=None):
        support_ozn = True
        globals_dir = 'gecode'
        super().__init__(support_ozn, globals_dir)

        self.cmd = path or 'fzn-gecode'

    def solve(self, fzn_file, *, check_complete=False, timeout=0, parallel=1,
              n_solns=-1, seed=0, restart=None, restart_base=None,
              restart_scale=None, suppress_segfault=False, **kwargs):
        """
        Solves a constrained optimization problem using the Gecode solver.

        :param str fzn_file: The path to the fzn file containing the problem to
                            be solved
        :param int n_solns: The number of solutions to output (0 = all,
                            -1 = one/best); default is -1
        :param int parallel: The number of threads to use to solve the problem
                            (0 = #processing units); default is 1
        :param int time: The time cutoff in milliseconds, after which the
                        execution is truncated and the best solution so far is
                        returned, 0 means no time cutoff; default is 0
        :param int seed: random seed; default is 0
        :param str restart: restart sequence type; default is None
        :param str restart_base: base for geometric restart sequence; if None (
                                default) the default value of Gecode is used,
                                which is 1.5
        :param str restart_scale: scale factor for restart sequence; if None (
                                default) the default value of Gecode is used,
                                which is 250
        :param bool suppress_segfault: whether to accept or not a solution
                                    returned when a segmentation fault has
                                    happened (this is unfortunately necessary
                                    sometimes due to some bugs in gecode).
        :return: A string containing the solution output stream of the execution
                of Gecode on the specified problem; it can be directly be given
                to the function solns2out to be transformed into output and
                then parsed
        :rtype: str
        """
        log = get_logger(__name__)

        args = [self.cmd]
        if n_solns >= 0:
            args.append('-n')
            args.append(n_solns)
        if parallel != 1:
            args.append('-p')
            args.append(parallel)
        if timeout > 0:
            args.append('-time')
            args.append(timeout)
        if seed != 0:
            args.append('-r')
            args.append(seed)
        if restart:
            args.append('-restart')
            args.append(restart)
        if restart_base:
            args.append('-restart-base')
            args.append(restart_base)
        if restart_scale:
            args.append('-restart-scale')
            args.append(restart_scale)
        args.append(fzn_file)

        try:
            process = run(args)
            if process.time >= timeout:
                complete = False
            out = process.stdout
        except CalledProcessError as err:
            if (suppress_segfault and len(err.stdout) > 0 and
                    err.stderr.startswith('Segmentation fault')):
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

    def __init__(self, path=None):
        support_ozn = False
        globals_dir = 'std'
        super().__init__(support_ozn, globals_dir)

        self.cmd = path or 'optimathsat'

    def solve(self, fzn_file, *, check_complete=False, **kwargs):
        """Simple proxy function to the OptiMathSat solver.

        This function is a simple interface to OptiMathSat which only specifies
        the input format as a FlatZinc model, without providing any additional
        arguments.

        :param str fzn_file: The path to the fzn file containing the problem to
                            be solved
        :return: A string containing the solution output stream of the execution
                of OptiMathSat on the specified problem
        :rtype: str
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

    def __init__(self, path=None):
        support_ozn = True
        globals_dir = 'opturion-cpx'
        super().__init__(support_ozn, globals_dir)

        self.cmd = path or 'fzn-cpx'

    def solve(self, fzn_file, *, check_complete=False, timeout=None, **kwargs):
        args = [self.cmd]

        if timeout:
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

# Default solvers
gecode = Gecode(path=config.get('gecode'))
opturion = Opturion(path=config.get('opturion'))
optimathsat = Optimathsat(path=config.get('optimathsat'))

