Tutorial
========

.. highlight:: minizinc
  :linenothreshold: 5

In this tutorial we will cover the basics of how to use PyMzn to solve MiniZinc
problems inside Python scripts. Bare in mind that this tutorial is not meant to
be an introduction to MiniZinc, so if you are new to MiniZinc go check out the
official `MiniZinc tutorial
<https://www.minizinc.org/doc-latest/en/part_2_tutorial.html>`__ and then come
back here to learn about how to use MiniZinc in Python.

Let's start with a simple coloring problem of Australia (which happens to be the
same of the MiniZinc tutorial):

.. literalinclude:: ../../examples/aust/aust.mzn
  :language: minizinc
  :caption: :download:`aust.mzn <../../examples/aust/aust.mzn>`
  :name: ex-aust
  :linenos:

Using PyMzn we can call MiniZinc to solve the above problem from a Python script
and get the result as a Python object. Calling PyMzn is just as easy as:

.. code-block:: python3

    import pymzn
    solns = pymzn.minizinc('aust.mzn')
    print(solns)

which will return a solution like:

.. code-block:: python3

    [{'wa': 3, 'nt': 2, 'sa': 1, 'q': 3, 'nsw': 2, 'v': 3, 't': 1}]

The ``pymzn.minizinc`` function takes as input the path to the MiniZinc file,
takes care of launching MiniZinc for you and parses the solution stream to get
back solutions as Python dictionaries. Internally, PyMzn takes care of how
solutions should be returned by MiniZinc in order to be able to parse them. By
default it will ignore the output statement on your MiniZinc model, so you can
leave it there, just in case. If instead you want to get solutions as strings
formatted according to the output statement present in your MiniZinc model, you
can use the option ``output_mode='item'`` with the ``pymzn.minizinc`` function:

.. code-block:: python3

    solns = pymzn.minizinc('aust.mzn', output_mode='item')
    print(solns[0])

which will print::

    wa=3     nt=2    sa=1
    q=3      nsw=2   v=3
    t=1

There are other options for the ``output_mode`` flag, namely ``dzn``, ``json``
and ``raw``. The former two return strings formatted as dzn and json
respectively, while the latter does not return a list of solutions but rather
the entire solution stream as a single string.

As you may have noticed, the ``pymzn.minizinc`` function returns an object of
type ``Solutions`` which in most cases may be addressed and iterated as a list:

.. code-block:: python3

    solns = pymzn.minizinc('aust.mzn')

    print(type(solns).__name__)
    # Solutions

    print(len(solns))
    # 1

    print(type(iter(solns)))
    # list_iterator

The ``Solutions`` object returned by the ``pymzn.minizinc`` function has also
few other useful attributes, such as the ``status`` attribute:

.. code-block:: python3

    solns = pymzn.minizinc('aust.mzn')

    print(solns.status)
    # Status.INCOMPLETE

The ``status`` attribute is an instance of a ``pymzn.Status`` enum, which
represents the status of the solution stream, i.e. wheter it is complete or not,
whether the problem is unsatisfiable or there has been an error with the solver.
In this case the status is incomplete because it is a satisfiability problem and
the solver returned only one of the feasible solution.

To get all the solutions of the problem, we can use the ``all_solutions`` flag:

.. code-block:: python3

    solns = pymzn.minizinc('aust.mzn', all_solutions=True)

    print(len(solns))
    # 18

    print(solns.status)
    # Status.COMPLETE

To be able to get all the solutions for a satisfiability problem, this feature
needs to be supported by the solver. The default solver used by PyMzn is Gecode,
which does support this feature.


Data
----

Let us now move on to another problem, a simple 0-1 knapsack encoded with
MiniZinc:

.. literalinclude:: ../../examples/knapsack/knapsack01.mzn
  :language: minizinc
  :caption: :download:`knapsack01.mzn <../../examples/knapsack/knapsack01.mzn>`
  :name: ex-knapsack
  :linenos:

As you can see, in the above problem some data is missing, so we need to specify
it via a data file or via inline data. Here is a data file for the above
problem:

.. literalinclude:: ../../examples/knapsack/knapsack01.dzn
  :language: minizinc
  :caption: :download:`knapsack01.dzn <../../examples/knapsack/knapsack01.dzn>`
  :name: ex-knapsack-dzn
  :linenos:

In the above file we are still missing the ``capacity`` parameter, which we can
specify as inline data. To solve the above problem with the provided data we
use:

.. code-block:: python3

    import pymzn
    solns = pymzn.minizinc('knapsack01.mzn', 'knapsack01.dzn', data={'capacity': 20})
    print(solns)
    # [{'x': {3, 5}}]

The second argument we passed to the ``pymzn.minizinc`` function is the data
file specified above. We also passed the keyword argument ``data`` as a
dictionary assigning the value ``20`` to the variable ``capacity``. PyMzn will
automatically convert the dictionary into an appropriate dzn representation and
pass it to MiniZinc as inline data. PyMzn does so by using the function
``pymzn.dict2dzn`` which you can use yourself:

.. code-block:: python3

    dzn = pymzn.dict2dzn({'capacity': 20})
    print(dzn)

which will return a list of dzn assignments, one for each variable, in this
case:

.. code-block:: python3

    ['capacity = 20;']

Conveniently, you can also save the dzn assignments directly on a file:

.. code-block:: python3

    pymzn.dict2dzn({'capacity': 20}, fout='capacity.dzn')

This file can then be used in subsequent calls to the ``pymzn.minizinc``
function. We can actually specify as many data files we need as additional
positional argument to the ``pymzn.minizinc`` function, so the above problem can
now be solved with:

.. code-block:: python3

    solns = pymzn.minizinc('knapsack01.mzn', 'knapsack01.dzn', 'capacity.dzn')
    print(solns)
    # [{'x': {3, 5}}]

If you want to get back the content of a data file into a Python dictionary,
PyMzn also offers the inverse function ``pymzn.dzn2dict``, which accepts the
path to a ``.dzn`` file as input and returns the content of the file converted
to Python objects:

.. code-block:: python3

    data = pymzn.dzn2dict('capacity.dzn')
    print(data)
    # {'capacity': 20}

The ``pymzn.dzn2dict`` function also accept dzn content directly:

.. code-block:: python3

    data = pymzn.dzn2dict('capacity = 20;')
    print(data)
    # {'capacity': 20}

You can read more about converting data to and from dzn format in the `Dzn files
<./reference/dzn/index.html>`__ section.


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

