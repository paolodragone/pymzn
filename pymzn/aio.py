"""\
PyMzn allows to execute minizinc concurrently within an event loop started by
Python's `asyncio` package. This allows to asyncronously solve one or more
models and collect their solutions as they are produced by the solver. This
could be useful in several situations, especially if the model returns a very
long stream of solutions or it takes more than few seconds to complete.
Executing the model asynchronously does not block the execution of the main
thread while waiting for the solver to terminate and provides a way to read
solutions as soon as they are found by the solver.

Consider the following simple model::

    %% configurations.mzn %%

    int: N = 7;
    array[1 .. N] of var 1 .. N: x;

    solve satisfy;

Suppose that you want to get all the solutions of the above problem, but you
need to do some other task while the solver does its work. We can execute
`minizinc` concurrently in this way::

    import pymzn
    import asyncio
    from pymzn.aio import minizinc

    async def run():
        solns = await minizinc('test.mzn', all_solutions=True)
        while solns.status is not pymzn.Status.COMPLETE:
            print('Performing some other task ...')
            await asyncio.sleep(1)
            for soln in solns:
                print(soln)

    if __name__ == '__main__':
        asyncio.run(run())


"""


try:
    from .mzn import aio as _aio
    from .mzn.aio import *
    __all__ = _aio.__all__
except SyntaxError as err:
    raise ImportError(
        'You need Python 3.6 or higher to use the pymzn.aio package.'
    ) from err

