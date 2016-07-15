PyMzn
=====

PyMzn is a Python wrapper for the `MiniZinc <http://minizinc.org>`__
tool pipeline. It is built on top of the libminizinc library (version 2.0)
and provides a number of off-the-shelf functions to readily solve problems
encoded in MiniZinc and parse the solutions into python objects.

Requirements
------------
PyMzn requires some additional software to be installed on your system
before you can use it properly, namely:

* The `libminizinc library <https://github.com/MiniZinc/libminizinc>`__;
* A CSP solver compatible with the FlatZinc encoding, e.g. `Gecode <http://www.gecode.org>`__.

Gecode is the default solver for PyMzn. If you use Gecode then PyMzn will work
out-of-the-box, otherwise, if you want to use a different solver, a little more
configuration is needed (see the
`documentation <http://paolodragone.com/pymzn/reference/solvers/>`__.)

Detailed instructions on how to install **libminizinc** and **Gecode** can be
found in the `documentation <http://paolodragone.com/pymzn/install.html>`__.

Install
-------

PyMzn can be installed via Pip:
::

    pip3 install pymzn

or otherwise from the source code:
::

    python3 setup.py install

Currently, PyMzn is developed and maintained in Python v3.5 with a
porting to Python v2.7 at every release (the branch does not contain the most
recent changes).

Usage
-----
First, you need a MiniZinc model encoding the problem you want to solve.
Here is a simple 0-1 knapsack problem encoded with MiniZinc:

::

    %% test.mzn %%
    int: n;
    set of int: OBJ = 1..n;
    int: capacity;
    array[OBJ] of int: profit;
    array[OBJ] of int: size;
    var set of OBJ: x;
    constraint sum(i in x)(size[i]) <= capacity;
    var int: obj = sum(i in x)(profit[i])
    solve maximize obj;

    %% test.dzn %%
    n = 5;
    profit = [10, 3, 9, 4, 8];
    size = [14, 4, 10, 6, 9];

You can solve the above problem using the PyMzn ``minizinc`` function:
::

    import pymzn
    pymzn.minizinc('test.mzn', 'test.dzn', data={'capacity': 20})

The result will be:
::

    [{'x': {3, 5}}]

The ``minizinc`` function automatically flattens the MiniZinc model, using the
provided mzn and dzn files, and the inline data provided. It executes the
solver on the flattened model and parses the solution stream to get the values
directly into Python.

PyMzn is also able to convert python objects to
`dzn <http://paolodragone.com/pymzn/reference/dzn/>`__ format and back,
interface with
`different solvers <http://paolodragone.com/pymzn/reference/solvers/>`__,
perform `dynamic modelling <http://paolodragone.com/pymzn/reference/model/>`__,
`serialization <http://paolodragone.com/pymzn/reference/minizinc/index.html#serialization>`__
of the problems to solve, and more.

For a follow-up of this example, read the
`Quick Start guide <http://paolodragone.com/pymzn/quick_start.html>`__.

For more information on the PyMzn functions read the
`Reference documentation <http://paolodragone.com/pymzn/reference/>`__

Contribute
----------

If you find a bug or think of a feature, please submit an issue on the
`GitHub page <https://github.com/paolodragone/pymzn/>`__ of PyMzn.

Pull requests are very welcome too. If you are interested in contributing to
the source code, read about the
`internal behavior <http://paolodragone.com/pymzn/internal.html>`__ of PyMzn.
Some things that would be really useful are:

* Implement specific interfaces for not yet supported solvers;
* Enhance existing ones.

Author
------

`Paolo Dragone <http://paolodragone.com>`__, PhD student at the University of
Trento.
