"""\
PyMzn provides a set of functions to deal with dzn encoded strings and
files. Using these functions it is possible to serialize Python objects
into dzn format and vice-versa. For instance, the ``pymzn.dict2dzn`` function
converts an assignment of variables (provided as a dictionary) into dzn
format:

.. code-block:: python3

    pymzn.dict2dzn({'a': 2, 'b': {4, 6}, 'c': {1, 2, 3}, 'd': {3: 4.5, 4: 1.3}, 'e': [[1, 2], [3, 4], [5, 6]]})

The output is a list of dzn statements, as for the previous example:

.. code-block:: python3

    ['a = 2;', 'b = {4, 6};', 'c = 1..3;', 'd = array1d(3..4, [4.5, 1.3]);', 'e = array2d(1..3, 1..2, [1, 2, 3, 4, 5, 6];']

Optionally, you can pass the path to a dzn file where to write the
statements.

.. code-block:: python3

    pymzn.dict2dzn(data, fout='path/to/dzn')

The supported types of python objects are: ``bool``, ``int``, ``float``,
``set``, ``list``, ``dict``. Lists are converted into dzn arrays with index-set
``1 .. len(list)``. Nested lists can be cast into MiniZinc multi-dimensional
array as well. Dictionaries are converted into dzn arrays with index-set equal
to the key-set of the dictionaryy, provided that the index-set is contiguous.
Nested combinations of the previous two are also allowed, provided that the
children of every node have the same index-set. The maximum depth is 6.

To evaluate back from dzn to python objects you can use the
``pymzn.dzn2dict`` function, which takes as input a dzn formatted
string or the path to a dzn file and returns the corresponding dictionary of
variable assignments. For instance, given the following dzn file:

.. code-block:: minizinc

    %% test.dzn %%

    a = 2;
    b = {4, 6};
    c = 1..3;
    d = array1d(3..4, [4.5, 1.3]);
    e = array2d(1..3, 1..2, [1, 2, 3, 4, 5, 6]);

Running the function:

.. code-block:: python3

    pymzn.dzn2dict('test.dzn')

will return:

.. code-block:: python3

    {'a': 2, 'b': {4, 6}, 'c': {1, 2, 3}, 'd': {3: 4.5, 4: 1.3}, 'e': [[1, 2], [3, 4], [5, 6]]}

which is identical to the object we serialized in the previous example.

In general, there is a one to one translation from python objects to dzn and
back, with the only exception of arrays with index-sets not based at 1. Arrays
and matrices based at 1 are translated into lists instead of dictionaries with
explicit keys. For instance:

.. code-block:: python3

    pymzn.dict2dzn({'a': {1: 2, 2: 4, 3: 6}})
    # ['a = array1d(1..3, [2, 4, 6]);']

but when translating back the array, whose index-set is based in 1, will be
translated into a list:

.. code-block:: python3

    pymzn.dzn2dict('a = array1d(1..3, [2, 4, 6]);')
    # {'a': [2, 4, 6]}

If you wish to avoid this behavior and get all arrays as dictionaries then you
can specify ``rebase_arrays=False`` as argument to the ``pymzn.dzn2dict``
function.

If, instead, you want to rebase also the arrays and matrices with different
index-sets you can use the ``pymzn.rebase_array`` function, which will discard
the index-sets in the dictionary representation of the array (matrix) and
transform it into a list (list of lists). For instance:

.. code-block:: python3

    pymzn.rebase_array({3: {2: 1, 3: 2, 4: 3}, 4: {1: 2, 2: 3}}, recursive=True)
    # [[1, 2, 3], [2, 3]]

Since version 0.18.0, PyMzn supports conversion of MiniZinc enums too:

.. code-block:: python3

    pymzn.dzn2dict('P = {A, B, C}; x = A;')
    # {'P': {'A', 'B', 'C'}, 'x': 'A'}

Without additional information, PyMzn converts enums values into strings and
enum types into sets of strings. In order to convert MiniZinc enums into Python
enums, we need to supply an additional keyword parameter ``types``, which is a
dictionary of MiniZinc types of the variables. In this case:

.. code-block:: python3

    data = pymzn.dzn2dict('P = {A, B, C}; x = A;', types={'P': 'enum', 'x': 'P'})
    print(data)

The result will be:

.. code-block:: python3

    {'x': <P.A: 1>}

where ``P.A`` is a value of an IntEnum ``P`` with three values ``P.A``, ``P.B``
and ``P.C``. By default, PyMzn will not include the enum types into the returned
dictionary of variable assignments. You can access the enum ``P`` with:

.. code-block:: python3

    P = type(data['x'])

    print(P)
    # <enum 'P'>

    print(list(P))
    # [<P.A: 1>, <P.B: 2>, <P.C: 3>]

If you want PyMzn to return the enum types along with the variable assignments,
you can do so by setting the ``return_enums`` flag to ``True``:

.. code-block:: python3

    data = pymzn.dzn2dict('P = {A, B, C}; x = A;', types={'P': 'enum', 'x': 'P'}, return_enums=True)
    print(data)
    # {'x': <P.A: 1>, 'P': <enum 'P'>}

When executing the ``pymzn.minizinc`` function, PyMzn will take care of
retrieving the types of the output variables from the model and will
automatically convert the enum values into python objects. You can also pass the
``return_enums=True`` option to ``pymzn.minizinc`` to obtain the same result as
the above example on all solutions returned.
"""

from . import marsh
from . import parse

__all__ = marsh.__all__ + parse.__all__

from .marsh import *
from .parse import *

