Tutorial
========

.. highlight:: minizinc
  :linenothreshold: 5

First, we need to define a constraint program via MiniZinc.
Here is a simple 0-1 knapsack problem encoded with MiniZinc:

.. literalinclude:: ../../examples/knapsack/knapsack01.mzn
  :language: minizinc
  :caption: :download:`knapsack01.mzn <../../examples/knapsack/knapsack01.mzn>`
  :name: ex-knapsack
  :linenos:

And here is a data file for the above problem:

.. literalinclude:: ../../examples/knapsack/knapsack01.dzn
  :language: minizinc
  :caption: :download:`knapsack01.dzn <../../examples/knapsack/knapsack01.dzn>`
  :name: ex-knapsack-dzn
  :linenos:


You can solve the above problem using the ``pymzn.minizinc`` function:

.. code-block:: python

    import pymzn
    solns = pymzn.minizinc('knapsack01.mzn', 'knapsack01.dzn', data={'capacity': 20})
    print(solns)

The result will be:

.. code-block:: python

    [{'x': {3, 5}}]

The returned object is a lazy solution stream, which can however be directly
referenced as a list. The default behavior is to evaluate the solutions into
python objects. Solutions are dictionaries containing variable assignments.

If you wish to override the default behavior and get a different output format
you can specify the ``output_mode`` argument. Possible formats are: ``dict``,
``item``, ``dzn``, ``json`` and ``raw``. The first is the default one. The
``item`` format will return strings formatted according to the output statement
in the input model. The ``dzn`` and ``json`` formats return strings formatted in
dzn or json respectively. The ``raw`` format, instead, returns the output of the
solver as a string without splitting the solutions. For instance, to get the
solution in ``dzn`` format:

.. code-block:: python

    pymzn.minizinc('test.mzn', output_mode='dzn')


Data
----

It is possible to specify data (.dzn) files to the ``minizinc`` function as
additional positional arguments:

.. code-block:: python

    pymzn.minizinc('test.mzn', 'data1.dzn', 'data2.dzn')

It is also possible to specify additional data inline along with the
``minizinc`` function:

.. code-block:: python

    pymzn.minizinc('test.mzn', 'data1.dzn', 'data2.dzn', data={'n': 10, 'm': [1,3,5]})

With the ``data`` argument you can specify an assignment of variables that will
be automatically converted into dzn format with the ``pymzn.dict2dzn`` function
(more details in the `Dzn files <./reference/dzn/index.html>`__ section).


Solver arguments
----------------

Usually, solvers provide arguments that can be used to modify their behavior.
You can specify arguments to pass to the solver as additional keyword arguments
in the ``minizinc`` function. For instance, adding the ``parallel`` argument,
you can specify how many threads should the solver use:

.. code-block:: python

    pymzn.minizinc('test.mzn', parallel=4)

Solver arguments are subject to the support of the solver. Some solver may also
provide additional parameters. More details in the `Solvers
<reference/solvers/>`__ section.

