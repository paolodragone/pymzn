
from ..dzn import dict2dzn, dzn2dict
from ..exceptions import *

from queue import Queue
from solutions import Solutions


class Parser:

    SOLN_SEP = '----------'
    SEARCH_COMPLETE = '=========='
    UNSATISFIABLE = '=====UNSATISFIABLE====='
    UNKNOWN = '=====UNKNOWN====='
    UNBOUNDED = '=====UNBOUNDED====='
    UNSATorUNBOUNDED = '=====UNSATorUNBOUNDED====='
    ERROR = '=====ERROR====='

    def __init__(self, mzn_file, solver, output_mode='dict'):
        self.mzn_file = mzn_file
        self.solver = solver
        self.output_mode = output_mode
        self._solns = None
        self.complete = False
        self.stats = None

    def _gather(self, solns, proc):
        try:
            for soln in self._parse(proc.stdout_data.splitlines()):
                solns.queue.put(soln)
            solns.complete = self.complete
            solns.stats = self.stats
        except MiniZincError as err:
            err._set(self.mzn_file, proc.stderr_data)
            raise err

    def parse(self, proc):
        queue = Queue()
        solns = Solutions(queue)
        self._gather(solns, proc)
        return solns

    def _parse(self, out):
        solns = self._split_solns(out)
        if self.output_mode == 'dict':
            solns = self._to_dict(solns)
        return solns

    def _split_solns(self, lines):
        """Split the solutions from the output stream of a solver or solns2out"""
        _buffer = []
        complete = False
        for line in lines:
            line = line.strip()
            if line == self.SOLN_SEP:
                yield '\n'.join(_buffer)
                _buffer = []
            elif line == self.SEARCH_COMPLETE:
                self.complete = True
                _buffer = []
            elif line == self.UNKNOWN:
                raise MiniZincUnknownError
            elif line == self.UNSATISFIABLE:
                raise MiniZincUnsatisfiableError
            elif line == self.UNBOUNDED:
                raise MiniZincUnboundedError
            elif line == self.UNSATorUNBOUNDED:
                raise MiniZincUnsatOrUnboundedError
            elif line == self.ERROR:
                raise MiniZincGenericError
            else:
                _buffer.append(line)
        self.stats = '\n'.join(_buffer)

    def _to_dict(self, stream):
        try:
            while True:
                yield dzn2dict(next(stream))
        except StopIteration as stop:
            return stop.value

