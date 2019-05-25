"""\
PyMzn supports asynchronous solving through Python coroutines. The package
``pymzn.aio`` contains the coroutine version of the standard ``pymzn.minizinc``
function. This coroutine allows to execute the minizinc as an asynchronous
process and to obtain intermediate solutions while the solver is still in
execution. This is useful e.g. when the solver may take a long time to finish
and one needs to keep track of the progress or when the number of returned
solutions is very high, so the MiniZinc process does not have to keep the
solutions in memory before the caller can start consuming them.

To use the ``minizinc`` coroutine, you need to have an event loop running in the
main thread of your application. Awaiting the ``minizinc`` coroutine produces a
lazy solution stream that, when addressed or iterated over returns all the
solutions found so far by the solver. The following is a full example of how to
use the ``minizinc`` coroutine:

.. literalinclude:: ../../../../examples/asyncronous/async.mzn
  :language: minizinc
  :caption: :download:`async.mzn <../../../../examples/asyncronous/async.mzn>`
  :name: ex-async-mzn
  :linenos:

.. literalinclude:: ../../../../examples/asyncronous/async_test.py
  :language: python3
  :caption: :download:`async.mzn <../../../../examples/asyncronous/async_test.py>`
  :name: ex-async
  :linenos:

This code will execute the ``main`` coroutine, which calls ``minizinc`` to find
all solutions of the ``async.mzn`` file. The option ``keep_solutions`` is set to
``False`` to avoid saving the solutions in memory. Each time the ``solns``
object is iterated over, it will return all the solutions found until that
point. Between iterations, a period 1 second is waited to simulate other work
performed on the main thread.
"""

from . import minizinc
from . import output

__all__ = minizinc.__all__ + output.__all__

from .minizinc import *
from .output import *

