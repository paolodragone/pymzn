PyMzn
=====

PyMzn is a Python library that wraps and enhances the `MiniZinc
<http://minzinc.org>`__ tools for CSP modelling and solving.  It is built on top
of the `minizinc <https://github.com/MiniZinc/MiniZincIDE>`__ toolkit and
provides a number of off-the-shelf functions to readily solve problems encoded
in MiniZinc and parse the solutions into Python objects.

Usage
-----
First, you need a MiniZinc model encoding the problem you want to solve.
Here is a simple 0-1 knapsack problem encoded with MiniZinc:::

    %% test.mzn %%
    int: n;                     % number of objects
    set of int: OBJ = 1..n;
    int: capacity;              % the capacity of the knapsack
    array[OBJ] of int: profit;  % the profit of each object
    array[OBJ] of int: size;    % the size of each object

    var set of OBJ: x;
    constraint sum(i in x)(size[i]) <= capacity;
    var int: obj = sum(i in x)(profit[i]);
    solve maximize obj;


    %% test.dzn %%
    n = 5;
    profit = [10, 3, 9, 4, 8];
    size = [14, 4, 10, 6, 9];

You can solve the above problem using the ``pymzn.minizinc`` function::

    import pymzn
    pymzn.minizinc('test.mzn', 'test.dzn', data={'capacity': 20})

The result will be::

    SolnStream(solns=[{'x': {3, 5}}], complete=True)

The returned object represent a solution stream, which can be directly
referenced and iterated as a list. The ``minizinc`` function automatically
flattens the MiniZinc model, using the provided mzn and dzn files. It executes
the solver on the flattened model and parses the solution stream to get the
solutions as Python dictionaries.

PyMzn is also able to:

* Convert python objects to `dzn <http://paolodragone.com/pymzn/reference/dzn/>`__ format and back;
* Interface with `different solvers <http://paolodragone.com/pymzn/reference/solvers/>`__;
* Perform `dynamic modelling <http://paolodragone.com/pymzn/reference/model/>`__;
* `Serialize <http://paolodragone.com/pymzn/reference/serialization.html>`__ several instances of one problem;
* and more ...

For a follow-up of this example, read the
`Quick Start guide <http://paolodragone.com/pymzn/quick_start.html>`__.

For more information on the PyMzn functions read the
`reference manual <http://paolodragone.com/pymzn/reference/>`__.


Install
-------

PyMzn can be installed via Pip::

    pip3 install pymzn

or from the source code available
on `GitHub <https://github.com/paolodragone/pymzn>`__::

    python3 setup.py install

Currently, PyMzn is developed and maintained in Python v3.5 with a
porting to Python v2.7 at every release (the python2 branch does not always
contain the most recent changes).


Requirements
------------
PyMzn requires some additional software to be installed on your system
before you can use it properly, namely:

* The `MiniZinc toolkit <https://github.com/MiniZinc/MiniZincIDE>`__;
* A CSP solver compatible with the FlatZinc encoding, e.g. `Gecode <http://www.gecode.org>`__.

You can use any solver you like, but the default one for PyMzn is `Gecode
<http://www.gecode.org>`__. If you use the Gecode solver, PyMzn will work
out-of-the-box. PyMzn also supports most of the solvers included in the MiniZinc
toolkit. If the solver you are looking for is not supported by PyMzn you can
implement your own interface and use it with little configuration (see the
`Solvers section <reference/solvers/>`__).

Detailed instructions on how to install *MiniZinc* and *Gecode* can be found in
the `Install section <http://paolodragone.com/pymzn/install.html>`__ of the
documentation.


Contribute
----------

If you find a bug or think of a useful feature, please submit an issue on the
`GitHub page <https://github.com/paolodragone/pymzn/>`__ of PyMzn.

Pull requests are very welcome too. If you are interested in contributing to
the PyMzn source code, read about its
`implementation details <http://paolodragone.com/pymzn/reference/internal.html>`__.
Some things that would be very useful are:

* Implement specific interfaces for not yet supported solvers;
* Enhance existing ones.


Heads up on future changes
--------------------------

Be aware that this project is still currently under development and thus it is
not in a stable version yet. Things in the future *will* certainly change. This
is especially due to recent changes in the minizinc library, which are
introducing lots of new features that could make some of PyMzn's features
obsolete. At any rate, PyMzn will stay updated to the most recent changes in
MiniZinc and keep enhancing its python interface.


Author
------

`Paolo Dragone <http://paolodragone.com>`__, PhD student at the University of
Trento.
