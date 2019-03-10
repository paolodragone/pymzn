
import asyncio
from functools import partial

from ... import config, logger

from ..solvers import gecode

from ..minizinc import (
    _minizinc_preliminaries, _flattening_args, _solve_args, _cleanup
)

from .process import start_process
from .output import AsyncSolutionParser


__all__ = ['minizinc', 'solve']


async def _start_minizinc_proc(*args, input=None):
    args = [config.minizinc] + list(args)
    logger.debug('Starting minizinc with arguments: {}'.format(args))
    return await start_process(*args, stdin=input)


async def _collect(proc, queue):
    async for line in proc.readlines():
        await queue.put(line)


def _cleanup_cb(files, task):
    _cleanup(files)


async def minizinc(
    mzn, *dzn_files, args=None, data=None, include=None, stdlib_dir=None,
    globals_dir=None, declare_enums=True, allow_multiple_assignments=False,
    keep=False, output_vars=None, output_base=None, output_mode='dict',
    solver=None, timeout=None, two_pass=None, pre_passes=None,
    output_objective=False, non_unique=False, all_solutions=False,
    num_solutions=None, free_search=False, parallel=None, seed=None,
    rebase_arrays=True, keep_solutions=True, return_enums=False,
    max_queue_size=0, **kwargs
):
    """Coroutine version of the ``pymzn.minizinc`` function.

    Parameters
    ----------
    max_queue_size : int
        Maximum number of solutions in the queue between the solution parser and
        the returned solution stream. When the queue is full, the solver
        execution will halt untill an item of the queue is consumed. This option
        is useful for memory management in cases where the solution stream gets
        very large and the caller cannot consume solutions as fast as they are
        produced. Use with care, if the full solution stream is not consumed
        before the execution of the Python program ends it may result in the
        solver becoming a zombie process. Default is ``0``, meaning an infinite
        queue.
    """

    mzn_file, dzn_files, data_file, data, keep, _output_mode, types = \
        _minizinc_preliminaries(
            mzn, *dzn_files, args=args, data=data, include=include,
            stdlib_dir=stdlib_dir, globals_dir=globals_dir,
            output_vars=output_vars, keep=keep, output_base=output_base,
            output_mode=output_mode, declare_enums=declare_enums,
            allow_multiple_assignments=allow_multiple_assignments
        )

    if not solver:
        solver = config.get('solver', gecode)

    solver_args = {**kwargs, **config.get('solver_args', {})}

    proc = await solve(
        solver, mzn_file, *dzn_files, data=data, include=include,
        stdlib_dir=stdlib_dir, globals_dir=globals_dir,
        output_mode=_output_mode, timeout=timeout, two_pass=two_pass,
        pre_passes=pre_passes, output_objective=output_objective,
        non_unique=non_unique, all_solutions=all_solutions,
        num_solutions=num_solutions, free_search=free_search, parallel=parallel,
        seed=seed, allow_multiple_assignments=allow_multiple_assignments,
        **solver_args
    )

    if output_mode == 'raw':
        solns = asyncio.Queue(maxsize=max_queue_size)
        task = asyncio.create_task(_collect(proc, solns))
    else:
        parser = AsyncSolutionParser(
            solver, output_mode=output_mode, rebase_arrays=rebase_arrays,
            types=types, keep_solutions=keep_solutions,
            return_enums=return_enums, max_queue_size=max_queue_size
        )
        solns = await parser.parse(proc)
        task = parser.parse_task

    if not keep:
        task.add_done_callback(partial(_cleanup_cb, [mzn_file, data_file]))

    return solns


async def solve(
    solver, mzn, *dzn_files, data=None, include=None, stdlib_dir=None,
    globals_dir=None, allow_multiple_assignments=False, output_mode='item',
    timeout=None, two_pass=None, pre_passes=None, output_objective=False,
    non_unique=False, all_solutions=False, num_solutions=None,
    free_search=False, parallel=None, seed=None, **kwargs
):
    args = _solve_args(
        solver, timeout=timeout, two_pass=two_pass, pre_passes=pre_passes,
        output_objective=output_objective, non_unique=non_unique,
        all_solutions=all_solutions, num_solutions=num_solutions,
        free_search=free_search, parallel=parallel, seed=seed, **kwargs
    )

    args += _flattening_args(
        mzn, *dzn_files, data=data, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir, output_mode=output_mode, include=include,
        allow_multiple_assignments=allow_multiple_assignments
    )

    input = mzn if args[-1] == '-' else None
    proc = await _start_minizinc_proc(*args, input=input)
    logger.debug('Solving process started.')
    return proc

