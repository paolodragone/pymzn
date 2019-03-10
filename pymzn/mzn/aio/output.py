
import asyncio

from ..output import SolutionParser, Solutions


class AsyncSolutionParser(SolutionParser):

    def __init__(
        self, solver, output_mode='dict', rebase_arrays=True, types=None,
        keep_solutions=True, return_enums=False, max_queue_size=0
    ):
        super().__init__(
            solver, output_mode=output_mode, rebase_arrays=rebase_arrays,
            types=types, keep_solutions=keep_solutions,
            return_enums=return_enums
        )
        self.max_queue_size = max_queue_size
        self.parse_task = None

    async def _collect(self, solns, proc):
        async for soln in self._parse(proc):
            await solns._queue.put(soln)
        solns.status = self.status
        solns.stderr = proc.stderr_data
        solns.log = self.solver_parser.log

    async def parse(self, proc):
        solns = Solutions(
            asyncio.Queue(maxsize=self.max_queue_size), keep=self.keep_solutions
        )
        self.parse_task = asyncio.create_task(self._collect(solns, proc))
        return solns

    async def _parse(self, proc):
        parse_lines = self._parse_lines()
        parse_lines.send(None)
        async for line in proc.readlines():
            line = line.decode('utf-8')
            soln = parse_lines.send(line)
            if soln is not None:
                yield soln

