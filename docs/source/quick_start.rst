Quick Start
===========
First, you need a MiniZinc model encoding the problem you want to solve.
Here is a simple 0-1 knapsack problem encoded with MiniZinc::

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
referenced and iterated as a list. The default behavior is to evaluate the
solutions into python objects. Solutions are dictionaries containing variable
assignments. The solution evaluation by PyMzn uses either json (when available)
or dzn as intermediate format from the solver. More details on how PyMzn works
internally are available in the `Implementation details <reference/internal>`__
section).

If you wish to override the default behavior and get a different output format
you can specify the ``output_mode`` argument. Possible formats are: ``dict``,
``item``, ``dzn`` and ``json``. The first is the default one. The ``item``
format will return strings formatted according to the output statement in the
input model. The ``dzn`` and ``json`` formats return strings formatted in dzn or
json respectively. The latter two formats are only available if the solver used
supports them.

::
    pymzn.minizinc('test.mzn', eval_output=False)


Data
----

It is possible to specify data (.dzn) files to the ``minizinc`` function as
additional positional arguments::

    pymzn.minizinc('test.mzn', 'data1.dzn', 'data2.dzn')

It is also possible to specify additional data inline with the ``minizinc``
function::

    pymzn.minizinc('test.mzn', 'data1.dzn', 'data2.dzn', data={'n': 10, 'm': [1,3,5]})

With the ``data`` argument you can specify an assignment of variables that will
be automatically converted to dzn format with the ``pymzn.dict2dzn`` function
(more details in the `Dzn files <reference/dzn/>`__ section).

Solver's arguments
------------------

Usually, solvers provide arguments that can be used to modify their behavior.
You can specify arguments to pass to the solver as additional keyword arguments
in the ``minizinc`` function. For instance, using the argument ``timeout`` for
Gecode, it will set a time cut-off (in seconds) for the problem solving::

    pymzn.minizinc('test.mzn', timeout=30)  # 30 seconds cut-off

Adding the ``parallel`` argument, you can specify how many threads
should Gecode use for the problem solving::

    pymzn.minizinc('test.mzn', timeout=30, parallel=4)

More details on available options are in the `Solvers <reference/solvers/>`__
section.
