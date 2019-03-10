
import sys
from enum import IntEnum
from .. import dzn2dict

from queue import Queue


__all__ = ['Status', 'Solutions']


SOLN_SEP = '----------'
SEARCH_COMPLETE = '=========='
UNKNOWN = '=====UNKNOWN====='
UNSATISFIABLE = '=====UNSATISFIABLE====='
UNBOUNDED = '=====UNBOUNDED====='
UNSATorUNBOUNDED = '=====UNSATorUNBOUNDED====='
ERROR = '=====ERROR====='


class Status(IntEnum):
    """Status of the solution stream."""

    #: The solution stream is complete (all solutions for satisfaction problems,
    #: optimal solution for optimization problems)
    COMPLETE = 0

    #: The solution stream is incomplete
    INCOMPLETE = 1

    #: The solution stream is empty (no solution found in the time limit)
    UNKNOWN = 2

    #: The problem admits no solution
    UNSATISFIABLE = 3

    #: The problem admits infinite solutions (unbounded domain)
    UNBOUNDED = 4

    #: Either unsatisfiable or unbounded
    UNSATorUNBOUNDED = 5

    #: Generic error in the execution of the solver
    ERROR = 6


class Solutions:
    """Solution stream returned by the ``pymzn.minizinc`` function.

    You should not need to instantiate this class in any other way than by
    calling the ``pymzn.minizinc`` or the ``pymzn.aio.minizinc`` functions.
    This class represents lazy list-like objects that collect the solutions
    provided by the solver and parsed by the PyMzn solution parser. The solution
    parser provides solutions to this object through a queue that is only
    accessed when this object is addressed or iterated over. If the queue has
    limited size (by using the ``max_queue_size`` option of the
    ``pymzn.aio.minizinc`` function), the execution of the solver will halt
    untill this object is addressed. Note that, by default, as soon as this
    object is addressed, the *full* queue is processed and it is cached in
    memory. To avoid this behavior, use the option ``keep_solutions=True`` in
    the ``pymzn.minizinc`` or ``pymzn.aio.minizinc`` functions.

    Arguments
    ---------
    status : Status
        The status of the solution stream, i.e. whether it is complete, the
        problem was unsatisfiable or other errors that might have occurred.
    log : str
        The log of the solver on standard output. Usually contains solver
        statistics and other log messages.
    stderr : str
        The log of the MiniZinc executable on standard error. Usually contains
        log messages about the flattening process, statistics and error
        messages.
    """

    def __init__(self, queue, *, keep=True):
        self._queue = queue
        self._keep = keep
        self._solns = [] if keep else None
        self._n_solns = 0
        self.status = Status.INCOMPLETE
        self.log = None
        self.stderr = None

    def _fetch(self):
        while not self._queue.empty():
            soln = self._queue.get_nowait()
            if self._keep:
                self._solns.append(soln)
            self._n_solns += 1
            yield soln

    def _fetch_all(self):
        for soln in self._fetch():
            pass

    def __len__(self):
        if self._keep:
            self._fetch_all()
        return self._n_solns

    def __iter__(self):
        if self._keep:
            self._fetch_all()
            return iter(self._solns)
        else:
            return self._fetch()

    def __getitem__(self, key):
        if not self._keep:
            raise RuntimeError(
                'Cannot address directly if keep_solutions is False'
            )
        self._fetch_all()
        return self._solns[key]

    def _pp_solns(self):
        if len(self._solns) <= 1:
            return str(self._solns)
        pp = ['[']
        for i, soln in enumerate(self._solns):
            pp.append('    ' + repr(soln))
            if i < len(self._solns) - 1:
                pp[-1] += ','
        pp.append(']')
        return '\n'.join(pp)

    def __repr__(self):
        if self._keep and self.status < 2:
            self._fetch_all()
            if len(self._solns) > 0:
                return '<Solutions: {}>'.format(self._pp_solns())
        return '<Solutions: {}>'.format(self.status.name)

    def __str__(self):
        if self._keep and self.status < 2:
            self._fetch_all()
            if len(self._solns) > 0:
                return self._pp_solns()
        return self.status.name

    def print(self, output_file=sys.stdout, log=False):
        """Print the solution stream"""

        for soln in iter(self):
            print(soln, file=output_file)
            print(SOLN_SEP, file=output_file)

        if self.status == 0:
            print(SEARCH_COMPLETE, file=output_file)

        if (self.status == 1 and self._n_solns == 0) or self.status >= 2:
            print({
                Status.INCOMPLETE : ERROR,
                Status.UNKNOWN: UNKNOWN,
                Status.UNSATISFIABLE: UNSATISFIABLE,
                Status.UNBOUNDED: UNBOUNDED,
                Status.UNSATorUNBOUNDED: UNSATorUNBOUNDED,
                Status.ERROR: ERROR
            }[self.status], file=output_file)

            if self.stderr:
                print(self.stderr.strip(), file=sys.stderr)

        elif log:
            print(str(self.log), file=output_file)


class SolutionParser:

    def __init__(
        self, solver, output_mode='dict', rebase_arrays=True, types=None,
        keep_solutions=True, return_enums=False
    ):
        self.solver = solver
        self.solver_parser = self.solver.parser()
        self.output_mode = output_mode
        self.rebase_arrays = rebase_arrays
        self.types = types
        self.keep_solutions = keep_solutions
        self.return_enums = return_enums
        self.status = Status.INCOMPLETE

    def _collect(self, solns, proc):
        for soln in self._parse(proc):
            solns._queue.put(soln)
        solns.status = self.status
        solns.stderr = proc.stderr_data
        solns.log = self.solver_parser.log

    def parse(self, proc):
        solns = Solutions(Queue(), keep=self.keep_solutions)
        self._collect(solns, proc)
        return solns

    def _parse(self, proc):
        parse_lines = self._parse_lines()
        parse_lines.send(None)
        for line in proc.readlines():
            soln = parse_lines.send(line)
            if soln is not None:
                yield soln

    def _parse_lines(self):
        solver_parse_out = self.solver_parser.parse_out()
        split_solns = self._split_solns()
        solver_parse_out.send(None)
        split_solns.send(None)

        line = yield
        while True:
            line = solver_parse_out.send(line)
            soln = split_solns.send(line)
            if soln is not None:
                if self.output_mode == 'dict':
                    soln = dzn2dict(
                        soln, rebase_arrays=self.rebase_arrays,
                        types=self.types, return_enums=self.return_enums
                    )
                line = yield soln
            else:
                line = yield

    def _split_solns(self):
        _buffer = []
        line = yield
        while True:
            line = line.strip()
            if line == SOLN_SEP:
                line = yield '\n'.join(_buffer)
                _buffer = []
                continue
            elif line == SEARCH_COMPLETE:
                self.status = Status.COMPLETE
                _buffer = []
            elif line == UNKNOWN:
                self.status = Status.UNKNOWN
            elif line == UNSATISFIABLE:
                self.status = Status.UNSATISFIABLE
            elif line == UNBOUNDED:
                self.status = Status.UNBOUNDED
            elif line == UNSATorUNBOUNDED:
                self.status = Status.UNSATorUNBOUNDED
            elif line == ERROR:
                self.status = Status.ERROR
            elif line:
                _buffer.append(line)
            line = yield

