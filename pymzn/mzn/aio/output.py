
import asyncio

from ..output import SolutionParser, Solutions


__all__ = ['AsyncSolutionParser']


class AsyncFileReader:

    def __init__(self, path, mode='rb', max_queue_size=64):
        self.fd = open(path, mode)
        self._queue = asyncio.Queue(maxsize=max_queue_size)
        self.stderr = ''

    async def start_reading(self):
        for line in self.fd:
            await self._queue.put(line)
        await self._queue.put(b'')
        self.fd.close()

    async def readlines(self):
        while True:
            line = await self._queue.get()
            if line == b'':
                break
            yield line


class AsyncSolutionParser(SolutionParser):
    """Asynchronous parser of a solution stream.

    This class is used when calling the `minizinc` function to parse the output
    of the solver. A `SolutionParser` can also be instantiated and used to parse
    a solution stream from a file-like object. This can be useful, for instance,
    when saving a solution stream on a file and parsing it later.

    Arguments
    ---------
    solver : Solver
        The solver used to generate the solution stream.
    output_mode : {'dict', 'item', 'dzn', 'json', 'raw'}
        The desired output format. The default is ``'dict'`` which returns a
        stream of solutions decoded as python dictionaries. The ``'item'``
        format outputs a stream of strings as returned by the ``solns2out``
        tool, formatted according to the output statement of the MiniZinc model.
        The ``'dzn'`` and ``'json'`` formats output a stream of strings
        formatted in dzn of json respectively. The ``'raw'`` format, instead
        returns the whole solution stream, without parsing.
    rebase_arrays : bool
        Whether to "rebase" parsed arrays (see the `Dzn files
        <http://paolodragone.com/pymzn/reference/dzn>`__ section). Default is
        True.
    types : dict
        Dictionary of variable types. Types can either be dictionaries, as
        returned by the ``minizinc --model-types-only``, or strings containing a
        type in dzn format. If the type is a string, it can either be the name
        of an enum type or one of the following: ``bool``, ``int``, ``float``,
        ``enum``, ``set of <type>``, ``array[<index_sets>] of <type>``. The
        default value for ``var_types`` is ``None``, in which case the type of
        most dzn assignments will be inferred automatically from the value. Enum
        values can only be parsed if their respective types are available.
    keep_solutions : bool
        Whether to keep the generated solutions in memory once retrieved by the
        returned `Solutions` object. See the description of the `Solutions`
        class for more details.
    return_enums : bool
        Whether to return the parsed enum types included in the dzn content.
    max_queue_size : int
        Maximum number of elements that can be held in memory by the queue
        between the parser and the `Solutions` object returned by the `parse`
        function. This can be useful when the solution stream is very large and
        cannot fit all in memory. By default the queue is infinite.
    """

    def __init__(
        self, solver=None, output_mode='dict', rebase_arrays=True, types=None,
        keep_solutions=True, return_enums=False, max_queue_size=0
    ):
        super().__init__(
            solver=solver, output_mode=output_mode, rebase_arrays=rebase_arrays,
            types=types, keep_solutions=keep_solutions,
            return_enums=return_enums
        )
        self.max_queue_size = max_queue_size
        self.parse_task = None

    async def parse_file(self, path, max_queue_size=64):
        proc = AsyncFileReader(path, max_queue_size=max_queue_size)
        asyncio.create_task(proc.start_reading())
        return await self.parse(proc)

    async def parse(self, proc):
        solns = Solutions(
            asyncio.Queue(maxsize=self.max_queue_size), keep=self.keep_solutions
        )
        self.parse_task = asyncio.create_task(self._collect(solns, proc))
        return solns

    async def _collect(self, solns, proc):
        async for soln in self._parse(proc):
            await solns._queue.put(soln)
        solns.status = self.status
        solns.stderr = proc.stderr_data
        solns.log = self.solver_parser.log

    async def _parse(self, proc):
        parse_lines = self._parse_lines()
        parse_lines.send(None)
        async for line in proc.readlines():
            line = line.decode('utf-8')
            soln = parse_lines.send(line)
            if soln is not None:
                yield soln

