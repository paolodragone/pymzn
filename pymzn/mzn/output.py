
import sys
from enum import IntEnum
from ..dzn import dzn2dict

from queue import Queue


SOLN_SEP = '----------'
SEARCH_COMPLETE = '=========='
UNKNOWN = '=====UNKNOWN====='
UNSATISFIABLE = '=====UNSATISFIABLE====='
UNBOUNDED = '=====UNBOUNDED====='
UNSATorUNBOUNDED = '=====UNSATorUNBOUNDED====='
ERROR = '=====ERROR====='


class Status(IntEnum):
    COMPLETE = 0
    INCOMPLETE = 1
    UNKNOWN = 2
    UNSATISFIABLE = 3
    UNBOUNDED = 4
    UNSATorUNBOUNDED = 5
    ERROR = 6


class Solutions:
    """Represents a solution stream from the `minizinc` function.

    This class populates lazily but can be referenced and iterated as a list.

    Attributes
    ----------
    complete : bool
        Whether the stream includes the complete set of solutions. This means
        the stream contains all solutions in a satisfiability problem, or it
        contains the global optimum for maximization/minimization problems.
    """
    def __init__(self, queue, *, keep=True):
        self._queue = queue
        self._keep = keep
        self._solns = [] if keep else None
        self._n_solns = 0
        self.status = Status.INCOMPLETE
        self.statistics = None
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

    def print(self, output_file=sys.stdout, statistics=False):

        for soln in iter(self):
            print(soln, file=output_file)
            print(SOLN_SEP, file=output_file)

        if self.status <= 1:
            if self.status == 0:
                print(SEARCH_COMPLETE, file=output_file)
            if statistics:
                print(str(self.statistics), file=output_file)
        else:
            print({
                Status.UNKNOWN: UNKNOWN,
                Status.UNSATISFIABLE: UNSATISFIABLE,
                Status.UNBOUNDED: UNBOUNDED,
                Status.UNSATorUNBOUNDED: UNSATorUNBOUNDED,
                Status.ERROR: ERROR
            }[solns.status], file=output_file)

            if self.stderr:
                print(self.stderr, file=sys.stderr)


class SolutionParser:

    def __init__(
        self, solver, output_mode='dict', rebase_arrays=True, types=None,
        keep_solutions=True
    ):
        self.solver = solver
        self.solver_parser = self.solver.parser()
        self.output_mode = output_mode
        self.rebase_arrays = rebase_arrays
        self.types = types
        self.keep_solutions = keep_solutions
        self.status = Status.INCOMPLETE

    def _collect(self, solns, proc):
        for soln in self._parse(proc):
            solns._queue.put(soln)
        solns.status = self.status
        solns.statistics = self.solver_parser.stats
        solns.stderr = proc.stderr_data

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
                        soln, rebase_arrays=self.rebase_arrays, types=self.types
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

