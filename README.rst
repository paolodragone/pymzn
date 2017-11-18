PyMzn
=====

**PyMzn** is a Python library that wraps and enhances the `MiniZinc
<http://minzinc.org>`__ tools for constraint programming. PyMzn is built on top
of the `minizinc <https://github.com/MiniZinc/MiniZincIDE>`__ toolkit and
provides a number of off-the-shelf functions to readily solve problems encoded
with the MiniZinc language and parse the solutions into Python objects.

Usage
-----
First, we need to define a constraint program via MiniZinc.
Here is a simple 0-1 knapsack problem encoded with MiniZinc::

    %% knapsack01.mzn %%
    int: n;                     % number of objects
    set of int: OBJ = 1..n;
    int: capacity;              % the capacity of the knapsack
    array[OBJ] of int: profit;  % the profit of each object
    array[OBJ] of int: size;    % the size of each object

    var set of OBJ: x;
    constraint sum(i in x)(size[i]) <= capacity;
    var int: obj = sum(i in x)(profit[i]);
    solve maximize obj;


    %% knapsack01.dzn %%
    n = 5;
    profit = [10, 3, 9, 4, 8];
    size = [14, 4, 10, 6, 9];

You can solve the above problem using the ``pymzn.minizinc`` function::

    import pymzn
    s = pymzn.minizinc('knapsack01.mzn', 'knapsack01.dzn', data={'capacity': 20})
    print(s)

The result will be::

    [{'x': {3, 5}}]

The returned object is a lazy solution stream, which can however be directly
referenced as a list. The ``minizinc`` function takes care of flattening the
MiniZinc model, launching the solver, and parsing the solutions into Python
dictionaries.

PyMzn is also able to:

* Convert python objects to `dzn <http://paolodragone.com/pymzn/reference/dzn/>`__ format and back;
* Interface with many different `solvers <http://paolodragone.com/pymzn/reference/solvers/>`__;
* Perform `dynamic modelling <http://paolodragone.com/pymzn/reference/model/>`__ through a Python interface or by embedding code from the `Jinja2 <http://jinja.pocoo.org/>`__ templating language;
* Safely `parallelize <http://paolodragone.com/pymzn/reference/serialization.html>`__ several instances of the same problem;
* and more ...

For a follow-up of the previous example, read the
`Quick Start guide <http://paolodragone.com/pymzn/quick_start.html>`__.

For more information on the PyMzn classes and functions refer to the
`reference manual <http://paolodragone.com/pymzn/reference/>`__.


Install
-------

PyMzn can be installed via Pip::

    pip install pymzn

or from the source code available
on `GitHub <https://github.com/paolodragone/pymzn/releases/latest>`__::

    python setup.py install

Currently, PyMzn is developed and maintained in Python 3.5 with a
porting to Python 2.7 at every release (the python2 branch does not always
contain the most recent changes).

Requirements
------------
PyMzn requires the MiniZinc toolkit to be installed on your machine, along with
at least one solver. The easiest way to install MiniZinc is to download the
`MiniZincIDE <https://github.com/MiniZinc/MiniZincIDE>`__ package, which
contains both the MiniZinc binaries and several solvers. After downloading the
package, make sure the executables are visible to PyMzn by either setting the
`PATH` environment variable or by configuring it using the `pymzn.config`
module.

For more details take a look at the `Install section
<http://paolodragone.com/pymzn/install.html>`__ in the documentation.


Contribute
----------

If you find a bug or think of a useful feature, please submit an issue on the
`GitHub page <https://github.com/paolodragone/pymzn/>`__ of PyMzn.

Pull requests are very welcome too. If you are interested in contributing to the
PyMzn source code, read about its `implementation details
<http://paolodragone.com/pymzn/reference/internal.html>`__.


Author
------

`Paolo Dragone <http://paolodragone.com>`__, PhD student at the University of
Trento (Italy).
