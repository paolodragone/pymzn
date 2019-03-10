PyMzn
=====

**PyMzn** is a Python library that wraps and enhances the
[MiniZinc](http://minizinc.org) tools for constraint programming. PyMzn is built
on top of the [minizinc](https://github.com/MiniZinc/MiniZincIDE) toolkit and
provides a number of off-the-shelf functions to readily solve problems encoded
with the MiniZinc language and return solutions as Python dictionaries.

Usage
-----
First, we need to define a constraint program via MiniZinc.
Here is a simple 0-1 knapsack problem encoded with MiniZinc:

``` minizinc
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
```

You can solve the above problem using the `pymzn.minizinc` function:

``` python3
    import pymzn
    solns = pymzn.minizinc('knapsack01.mzn', 'knapsack01.dzn', data={'capacity': 20})
    print(solns)
```

The result will be:

``` python3
    [{'x': {3, 5}}]
```

The returned object is a lazy solution stream, which can either be iterated or
directly indexed as a list. The `pymzn.minizinc` function takes care of all the
preprocessing, the communication with the `minizinc` executable, and the parsing
of the solutions stream into Python dictionaries.

PyMzn is also able to:

* Convert Python dictionaries to
  [dzn](http://paolodragone.com/pymzn/reference/dzn/) format and back (e.g. when
  passing data to the `pymzn.minizinc` function);
* Interface with many different
  [solvers](http://paolodragone.com/pymzn/reference/solvers/);
* [Preprocess](http://paolodragone.com/pymzn/reference/templates/) MiniZinc models
  by embedding code from the [Jinja2](http://jinja.pocoo.org/) templating
  language;
* Perform [concurrent](http://paolodragone.com/pymzn/reference/aio) MiniZinc
  execution using Python coroutines.

For a follow-up of the previous example, read the
[PyMzn tutorial](http://paolodragone.com/pymzn/tutorial.html).

For more information on the PyMzn classes and functions refer to the
[reference manual](http://paolodragone.com/pymzn/reference/).


Install
-------

PyMzn can be installed via Pip:

``` bash
    pip install pymzn
```

or from the source code available
on [GitHub](https://github.com/paolodragone/pymzn/releases/latest):

``` bash
    python setup.py install
```


Requirements
------------
PyMzn is developed and maintained in Python 3.5. Starting from version 0.18.0,
support for Python 2 and versions previous to 3.5 has been dropped (its just too
much work mainintaining them). Using the package `pymzn.aio` for concurrent
execution requires Python 3.6 (though it is optional).

PyMzn requires the MiniZinc toolkit to be installed on your machine. Starting
from PyMzn 0.18.0, the minimum MiniZinc version required is the 2.2.0. If you
need to work with previous versions of MiniZinc, PyMzn 0.17.1 should work fine.

The easiest way to install MiniZinc is to download the
[MiniZincIDE](https://github.com/MiniZinc/MiniZincIDE) package, which
contains both the MiniZinc binaries and several solvers. After downloading the
package, make sure the executables are visible to PyMzn either by setting the
`PATH` environment variable or by configuring it using the `pymzn.config`
module.

For more details take a look at the
[Install section](http://paolodragone.com/pymzn/install.html) in the
documentation.

Optional dependencies include:
* [Jinja2](http://jinja.pocoo.org/docs/intro/#installation), for preprocessing
  through Jinja templating language;
* [PyYAML](https://pyyaml.org/wiki/PyYAML) and
  [appdirs](https://github.com/ActiveState/appdirs), for loading and saving
  configuration files.

Author
------

[Paolo Dragone](http://paolodragone.com), PhD student at the University of
Trento (Italy).

