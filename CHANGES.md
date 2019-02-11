
PyMzn Change Log
================


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

