
import asyncio
from functools import partial

from ...config import config

from ...log import logger
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
    globals_dir=None, output_vars=None, keep=False, output_dir=None,
    output_mode='dict', solver=None, timeout=None, two_pass=None,
    pre_passes=None, output_objective=False, non_unique=False,
    all_solutions=False, num_solutions=None, free_search=False, parallel=None,
    seed=None, **kwargs
):

    (
        mzn_file, dzn_files, data, data_file, keep, _output_mode, solver,
        solver_args
    ) = _minizinc_preliminaries(
            mzn, *dzn_files, args=args, data=data, include=include,
            stdlib_dir=stdlib_dir, globals_dir=globals_dir,
            output_vars=output_vars, keep=keep, output_dir=output_dir,
            output_mode=output_mode, solver=solver, **kwargs
        )

    proc = await solve(
        solver, mzn_file, *dzn_files, data=data, include=include,
        stdlib_dir=stdlib_dir, globals_dir=globals_dir, keep=keep,
        output_mode=_output_mode, timeout=timeout, two_pass=two_pass,
        pre_passes=pre_passes, output_objective=output_objective,
        non_unique=non_unique, all_solutions=all_solutions,
        num_solutions=num_solutions, free_search=free_search, parallel=parallel,
        seed=seed, **solver_args
    )

    if output_mode == 'raw':
        solns = asyncio.Queue()
        task = asyncio.create_task(_collect(proc, solns))
    else:
        parser = AsyncSolutionParser(solver, output_mode=output_mode)
        solns = await parser.parse(proc)
        task = parser.parse_task

    if not keep:
        task.add_done_callback(partial(_cleanup_cb, [mzn_file, data_file]))

    return solns


async def solve(
    solver, mzn_file, *dzn_files, data=None, include=None, stdlib_dir=None,
    globals_dir=None, keep=False, output_mode='dict', timeout=None,
    two_pass=None, pre_passes=None, output_objective=False, non_unique=False,
    all_solutions=False, num_solutions=None, free_search=False, parallel=None,
    seed=None, **kwargs
):
    args = _flattening_args(
        mzn_file, *dzn_files, data=data, keep=keep, stdlib_dir=stdlib_dir,
        globals_dir=globals_dir, output_mode=output_mode, include=include
    )

    args += _solve_args(
        solver, timeout=timeout, two_pass=two_pass, pre_passes=pre_passes,
        output_objective=output_objective, non_unique=non_unique,
        all_solutions=all_solutions, num_solutions=num_solutions,
        free_search=free_search, parallel=parallel, seed=seed, **kwargs
    )

    proc = await _start_minizinc_proc(*args)
    logger.debug('Solving process started.')
    return proc

