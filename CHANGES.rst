
PyMzn changes
=============

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
  * Renamed ``path`` into ``include`` in the ``pymzn.minizinc`` and ``pymzn.mzn2fzn`` functions.
  * Introduced ``output_mode`` in place of ``parse_output`` and ``eval_output`` as parameter to the ``pymzn.minizinc`` function.

* Moved ``pymzn.run`` into utils
* Slim down the library quite a bit. Removed unnecessary stuff.
* Many bug fixes
