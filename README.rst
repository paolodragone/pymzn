PyMzn
=====

PyMzn is a Python library that wraps and enhances the
`MiniZinc <http://minzinc.org>`__ tools for CSP modelling and solving.
It is built on top of the libminizinc library (version 2.0)
and provides a number of off-the-shelf functions to readily solve problems
encoded in MiniZinc and parse the solutions into Python objects.

Usage
-----
First, you need a MiniZinc model encoding the problem you want to solve.
Here is a simple 0-1 knapsack problem encoded with MiniZinc:

::

    %% test.mzn %%
    int: n;  % number of objects
    set of int: OBJ = 1..n;
    int: capacity;  % the capacity of the knapsack
    array[OBJ] of int: profit;  % the profit of each object
    array[OBJ] of int: size;  % the size of each object

    var set of OBJ: x;
    constraint sum(i in x)(size[i]) <= capacity;
    var int: obj = sum(i in x)(profit[i])
    solve maximize obj;


    %% test.dzn %%
    n = 5;
    profit = [10, 3, 9, 4, 8];
    size = [14, 4, 10, 6, 9];

You can solve the above problem using the ``pymzn.minizinc`` function:
::

    import pymzn
    pymzn.minizinc('test.mzn', 'test.dzn', data={'capacity': 20})

The result will be:
::

    [{'x': {3, 5}}]

The ``minizinc`` function automatically flattens the MiniZinc model, using the
provided mzn and dzn files, and the inline data provided. It executes the
solver on the flattened model and parses the solution stream to get the
solutions as Python dictionaries.

PyMzn is also able to:

* Convert python objects to
`dzn <http://paolodragone.com/pymzn/reference/dzn/>`__ format and back;

* Interface with
`different solvers <http://paolodragone.com/pymzn/reference/solvers/>`__;

* Perform `dynamic modelling <http://paolodragone.com/pymzn/reference/model/>`__;

* `Serialize <http://paolodragone.com/pymzn/reference/minizinc/index.html#serialization>`__
several instances of one problem;

* and more ...

For a follow-up of this example, read the
`Quick Start guide <http://paolodragone.com/pymzn/quick_start.html>`__.

For more information on the PyMzn functions read the
`documentation <http://paolodragone.com/pymzn/reference/>`__.


Install
-------

PyMzn can be installed via Pip:
::

    pip3 install pymzn

or from the source code available
on `GitHub <https://github.com/paolodragone/pymzn>`__:
::

    python3 setup.py install

Currently, PyMzn is developed and maintained in Python v3.5 with a
porting to Python v2.7 at every release (the python2 branch does not contain
the most recent changes).


Requirements
------------
PyMzn requires some additional software to be installed on your system
before you can use it properly, namely:

* The `libminizinc library <https://github.com/MiniZinc/libminizinc>`__;
* A CSP solver compatible with the FlatZinc encoding, e.g. `Gecode <http://www.gecode.org>`__.

You can use any solver you like, but the default one for PyMzn is
`Gecode <http://www.gecode.org>`__. If you use the Gecode solver, PyMzn will
work out-of-the-box, otherwise it will need some little configuration (see the
`Solvers section <reference/solvers/>`__).

Detailed instructions on how to install *libminizinc* and *Gecode* can be
found in the `Install section <http://paolodragone.com/pymzn/install.html>`__
of the documentation.


Contribute
----------

If you find a bug or think of a feature, please submit an issue on the
`GitHub page <https://github.com/paolodragone/pymzn/>`__ of PyMzn.

Pull requests are very welcome too. If you are interested in contributing to
the PyMzn source code, read about its
`internal behavior <http://paolodragone.com/pymzn/internal.html>`__.
Some things that would be very useful are:

* Implement specific interfaces for not yet supported solvers;
* Enhance existing ones.

Author
------

`Paolo Dragone <http://paolodragone.com>`__, PhD student at the University of
Trento.
