import pymzn
import asyncio
from pymzn.aio import minizinc

async def main():
    solns = await minizinc('async.mzn', all_solutions=True, keep_solutions=False)
    while solns.status is not pymzn.Status.COMPLETE:
        await asyncio.sleep(1)
        for i, soln in enumerate(solns):
            if i == 0:
                print(soln)

asyncio.run(main())
