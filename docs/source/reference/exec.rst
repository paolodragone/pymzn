PyMzn executable
================

PyMzn comes with a command line executable that provides a direct interface to
PyMzn for solving MiniZinc programs, in much the same way of the ``minizinc``
executable. The added benefit is that the ``pymzn`` program provides support for
templating arguments and other PyMzn options. Using the example found in the
`Templates <./templates/>`__ section, one can solve the problem with
compatibility constraint directly from the command line with::

    pymzn minizinc knapsack.pmzn knapsack.dzn compatibility.dzn --args "{'with_compatibility': True}"

which prints to standard output::

    {'x': {1, 5}}
    ----------
    ==========

The ``pymzn`` command can also be used to get and set permanent system-wide
configuration like::

    pymzn config minizinc /path/to/minizinc

