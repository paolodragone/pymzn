"""

PyMzn provides a set of functions to deal with dzn encoded strings and
files. Using these functions it is possible to serialize Python objects
into dzn format and vice-versa. For instance, the ``pymzn.dzn`` function
converts an assignment of variables (provided as a dictionary) into dzn
format:::

    pymzn.dzn({'a': 2, 'b': {4, 6}, 'c': {1, 2, 3}, 'd': {3: 4.5, 4: 1.3}, 'e': [[1, 2], [3, 4], [5, 6]]})

The output is a list of dzn statements, as for the previous example:::

    ['a = 2;', 'b = {4, 6};', 'c = 1..3;', 'd = array1d(3..4, [4.5, 1.3]);', 'e = array2d(1..3, 1..2, [1, 2, 3, 4, 5, 6];']

Optionally, you can pass the path to a dzn file where to write the
statements.

::

    pymzn.dzn(data, fout='path/to/dzn')

The supported types of python objects are: \* Booleans \* Integers \*
Floats \* Sets \* Multi-dimensional arrays: \* lists are converted into
dzn arrays with index-set 1..len(list); \* dicts are converted into dzn
arrays with index-set equal to the key-set of the dict, provided that
the index-set is contiguous; \* nested combinations of the previous two,
provided that the children of every node have the same index-set. The
maximum depth is 6.

To evaluate back from dzn to python objects you can use the
``pymzn.dzn_eval`` function, which takes as input a dzn formatted
string or the path to a dzn file and returns the corresponding dictionary of
variable assignments. For instance, given the following dzn file:::

    %% test.dzn %%

    a = 2;
    b = {4, 6};
    c = 1..3;
    d = array1d(3..4, [4.5, 1.3]);
    e = array2d(1..3, 1..2, [1, 2, 3, 4, 5, 6]);

Running the function:::

    pymzn.dzn_eval('test.dzn')

will return:::

    {'a': 2, 'b': {4, 6}, 'c': {1, 2, 3}, 'd': {3: 4.5, 4: 1.3}, 'e': [[1, 2], [3, 4], [5, 6]]}

which is identical to the object we serialized in the previous example.

In general, there is a one to one translation from python objects to dzn and
back, with the only exception of arrays with index-sets not based in 1. Arrays
and matrices based in 1 are translated into lists instead of dictionaries with
explicit keys. For instance:::

    pymzn.dzn({'a': {1: 2, 2: 4, 3: 6}})
    # returns: ['a = array1d(1..3, [2, 4, 6]);']

but when translating back the array, whose index-set is based in 1, will be
translated into a list:::

    pymzn.dzn_eval('a = array1d(1..3, [2, 4, 6]);')
    # returns: {'a': [2, 4, 6]}

If you wish to avoid this behavior and get all arrays as dictionaries then you
can specify ``rebase_arrays=False`` as argument for the ``pymzn.dzn_eval``
function.

If, instead, you want to rebase also the arrays and matrices with different
index-sets you can use the ``pymzn.rebase_array`` function, which will discard
the index-sets in the dictionary representation of the array (matrix) and
transform it into a list (list of lists). For instance:::

    pymzn.rebase_array({3: {2: 1, 3: 2, 4: 3}, 4: {1: 2, 2: 3}})
    # returns: [[1, 2, 3], [2, 3]]

"""

from ._marsh import *
from ._eval import *

__all__ = ['dzn', 'dzn_statement', 'dzn_value', 'rebase_array', 'dzn_eval']

