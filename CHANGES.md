
PyMzn Change Log
================

0.18.2
------

* Support parsing of saved solution streams.
* Bugfixes.


0.18.1
------

* Massive redesign of the whole pipeline using features from MiniZinc 2.2.0
  (earlier MiniZinc versions are no longer supported, yet PyMzn 0.17.1 should
  work fine for the most part).
* Now PyMzn interfaces only to the `minizinc` executable, greatly
  simplifying internal complexity.
* The `minizinc` function now only executes MiniZinc synchronously (i.e. wait
  for it to finish before parsing the solution stream).
* Asyncronous solving is now handled via Python's `asyncio` package. The new
  `pymzn.aio` module contains the `minizinc` *coroutine*, i.e. an asyncronous
  version of the `pymzn.minizinc` function. The `pymzn.aio` module requires
  Python >= 3.6.
* PyMzn can now parse MiniZinc enums into Python Enums and back.
* Substantial improvement of the preprocessing, solving and solution parsing.
* The `Solutions` class returned by the `minizinc` function has been improved
  too.
* Removed the `MiniZincModel` class for dynamic modelling, just use Jinja
  instead.
* Improved configuration facility.
* The `pymzn` command line executable has been greatly improved.
* This version is not backward compatible. Most of the existing code will need
  to be adapted.


0.16.0
------

* Introduced templating using Jinja2. The ``pymzn.MiniZincModel`` class can now
  compile templated models, and that is also done automatically using
  ``pymzn.minizinc``.
* The ``pymzn.templates`` added for managing template search.
* Substantially improve the API for managing external processes. Now the
  ``pymzn.Process`` class takes care of executing either synchronously or
  asynchronously an external process.
* The functions ``pymzn.minizinc`` and ``pymzn.solns2out`` have become
  asynchronous by default.
* The ``pymzn.minizinc`` now returns a instance of ``pymzn.Solutions``, which
  receives lazily the solutions from the solving pipeline, but can also be
  referenced as a list after receiving the full solution stream.
* Add ``num_solutions`` parameter to ``pymzn.minizinc``.
* API changes:
    * Deleted ``pymzn.utils`` module, along with the ``pymzn.run`` function
    * Added ``pymzn.process`` module
    * Renamed ``pymzn.SolnStream`` into ``pymzn.Solutions``
    * The function ``pymzn.solns2out`` now returns a generator
    * The function ``pymzn.minizinc`` is no longer blocking until the underlying
      solving process is completed. It now returns a ``pymzn.Solutions`` that
      can be lazily accessed.
    * Added ``solve_start`` method to ``pymzn.Solver`` class which returns a
      started process that produces solutions asynchronously.
* Several improvements and bug fixes.


0.14.0
------

* Function ``pymzn.minizinc`` now returns a ``SolnStream``
* Completely revisited ``pymzn.Solver`` abstract class.
* Added support to many new solvers:
    * Chuffed
    * CBC
    * Gurobi
    * G12 (fd, lazy, mip)
* API changes:
    * Renamed ``pymzn.dzn_eval`` into ``pymzn.dzn2dict``
    * Renamed ``pymzn.dzn`` into ``pymzn.dict2dzn``
    * Renamed ``pymzn.dzn_statement`` into ``pymzn.stmt2dzn``
    * Renamed ``pymzn.dzn_value`` into ``pymzn.val2dzn``
    * Renamed ``path`` into ``include`` in the ``pymzn.minizinc`` and
      ``pymzn.mzn2fzn`` functions.
    * Introduced ``output_mode`` in place of ``parse_output`` and
      ``eval_output`` as parameter to the ``pymzn.minizinc`` function.
* Moved ``pymzn.run`` into utils
* Slim down the library quite a bit. Removed unnecessary stuff.
* Many bug fixes

