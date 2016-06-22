`PyMzn <https://github.com/paolodragone/PyMzn>`__
=================================================

PyMzn is a Python 3 wrapper for the MiniZinc tool pipeline. It is built
on top of the libminizinc library (version 2.0) and provides a number of
off-the-shelf functions to readily solve problems encoded in MiniZinc
and parse the solutions into python objects.

Install
-------

To install PyMzn, you first need to download and compile libminizinc
from: https://github.com/MiniZinc/libminizinc/archive/master.zip
Instructions on how to compile libminizinc are provided in the package
itself. It is not necessary but strongly recommended to insert the path
to the directory containing the binaries of the libminizinc tools into
the PATH environment variable.

There is also a ``minizinc`` package available through ``apt-get``, but
it is an older version and PyMzn has not been tested with it, so we
recommend you to compile libminizinc from sources.

To use MiniZinc one also needs (at least) one compatible CSP solver
installed. The default one assumed by this library is Gecode 4.4.0,
which you can download from:
http://www.gecode.org/download/gecode-4.4.0.tar.gz In principle you can
use any solver you like, provided it is compatible with MiniZinc. If you
use a solver that is not Gecode, please read carefully the following
section *Solvers*.

After these preliminary steps, you can install PyMzn by either download
the source code from the git repository or install it via Pip:

::

    pip3 install pymzn

Quick Start
-----------

First thing, you need a MiniZinc model encoding the problem to solve.
Here is a simple 0-1 knapsack problem encoded with MiniZinc:

::

    %% test.mzn %%

    int: n = 5;
    set of int: OBJ = 1..n;
    int: capacity = 20;
    array[OBJ] of int: profit = [10, 3, 9, 4, 8];
    array[OBJ] of int: size = [14, 4, 10, 6, 9];

    var set of OBJ: x;
    constraint sum(i in x)(size[i]) <= capacity;

    solve maximize sum(i in x)(profit[i]);

Assuming that you have installed Gecode on your machine, you can solve
the above problem using the ``minizinc`` function of pymzn in the
following way:

::

    import pymzn
    pymzn.minizinc('test.mzn')

If you want to use a different solver, please read the following section
on *Solvers*.

If you did not specify the path to the binaries of libminizinc into the
PATH environment variable, you need to pass it to the ``minizinc``
function through the ``bin_path`` argument:

::

    pymzn.minizinc('test.mzn', bin_path='path/to/libminizinc')

The returned value will be:

::

    [{'x': {3, 5}}]

The output of the ``minizinc`` function is a list of solutions. Each
solution is a dictionary containing the assignment of each variable to
its value. The assignments are key-value pairs where the key is a string
containing the name of the variable in the mzn file. Each output value
can be automatically parsed and transformed into an equivalent value
using python structures. This is the default behaviour, but it only
works if no ``output`` statement is used in the minizinc model (or an
equivalent output format is provided), more about parsing in the
following section. The following list summarizes the Python types which
the MiniZinc types are converted to: \* int -> int \* float -> float \*
set -> set \* array1d -> dict {index: value} \* array2d -> dict of dict
{index: value} \* array3d -> ...

The array1d are converted to dictionaries because arrays in minizinc can
use as index-set any contiguous interval of integers, so it could have
some semantics associated with it. If the index-set is meaningless and
you prefer to work with lists, the ``pymzn`` module also provides the
convenience function ``dict2array`` which converts a dict-based array
(as from the output of the ``parse_dzn`` function) into a list-based
array, more suitable to represent vectors and matrices of numbers.

The behaviour of the ``minizinc`` function can be adjusted by passing
keywords arguments, which are listed and explained in detail in the
documentation. There is an almost one-to-one match with command line
arguments of the libminizinc utilities.

For instance, you can pass data to the ``minizinc`` function in the form
of a dictionary of python objects, which are then converted in the right
dzn format and fed to the mzn2fzn utility (more information about this
in the *Data* section).

::

    pymzn.minizinc('test.mzn', data={'n': 10})

Otherwise you can provide dzn files containing the data:

::

    pymzn.minizinc('test.mzn', dzn_files=['data1.dzn', 'data2.dzn'])

Or you can use both.

For more details on how to use each functions, please refer to the
documentation. To compile the documentation, first make sure you
installed Sphinx for Python 3, and then execute the make file inside the
``docs`` directory:

::

    make html

The documentation will then be compiled in the ``docs/_build/html``
folder.

Solvers
-------

If you want to use a different solver other than Gecode, you first need
to make sure that it supports the MiniZinc interface. To solve your
model through PyMzn using the selected solver, you need to provide a
proxy function to handle the command line interface of the solver, this
is an example of such function:

::

    import pymzn

    def fzn_solver(fzn_file, arg1=def_val1, arg2=def_val2):
        solver_path = 'path/to/solver'  # Only the name if it's in the PATH
        args = [('-arg1', arg1), ('-arg2', arg2), fzn_file]
        solver_cmd = pymzn.binary.command(solver_path, args)
        return pymzn.binary.run(solver_cmd, args)

Then you can run the ``minizinc`` function like this:

::

    pymzn.minizinc('test.mzn', fzn_cmd=fzn_solver, fzn_flags={'arg1':val1, 'arg2':val2})

Parsing output
--------------

The output stream of the solver is parsed by the ``solns2out`` function.
To parse the output one needs a specialized function. The default one is
the ``parse_dzn`` function. If no parsing function (``parse=None``) is
passed to the ``solns2out`` function then the raw output of the solver
is used as output solution stream. If a custom output statement is used
in the minizinc model, then an appropriate parsing function must be
provided as well.

The parsing function will be of the form:
``def parse_fun(lines):     for line in lines:        # parse the line        ...     # return parsed solution``
It gets as input the raw lines (as strings) of the output stream of the
solver. It is executed for each solution separately. It returns whatever
object you like to represent the solutions of the solver in your
application.

Data (dzn files)
----------------

The PyMzn library also provides a set of methods to convert python
objects into dzn format.

::

    pymzn.dzn({'a': 2, 'b': {4, 6}, 'c': {1, 2, 3}, 'd': {3: 4.5, 4: 1.3}, 'e': [[1, 2], [3, 4], [5, 6]]})

The ``dzn`` function gets a dictionary of python objects as input and
returns a list of variable declaration statements in dzn format. For
instance, the output of the previous example would be:

::

    ['a = 2;', 'b = {4, 6};', 'c = 1..3;', 'd = array1d(3..4, [4.5, 1.3]);', 'e = array2d(1..3, 1..2, [1, 2, 3, 4, 5, 6];']

Optionally, you can pass the path to a dzn file where to write the
statements.

::

    pymzn.dzn(data, fout='path/to/dzn')

The supported types of python objects are: \* String (str) \* Integer
(int) \* Float (float) \* Set (set of str, int of float) \*
Multi-dimensional arrays: \* list of str, int, float or set; lists are
converted into dzn arrays with index-set 1..len(list); \* dict with int
keys of str, int, float or set; dicts are converted into dzn arrays with
index-set equal to the key-set of the dict, provided that it is a
contiguous set; \* nested combinations of the previous two, provided
that the children of every node have the same index-set. The maximum
depth is 6.

Troubleshooting
---------------

-  Gecode raises the following error at the first execution after the
   installation:
   ``fzn-gecode: error while loading shared libraries: libgecodeflatzinc.so.41: cannot open shared object file: No such file or directory``
   To solve this problem you need to set the environment variable
   ``LD_LIBRARY_PATH`` before running your Python script:
   ``export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib/`` or put
   the script into your ``~/.bashrc`` file and then run:
   ``source ~/.bashrc``

-  Minizinc raises the following error when trying to include the gecode
   library with the ``-G gecode`` option:
   ``Cannot access include directory /usr/local/bin/../share/minizinc/gecode/``
   To solve this problem you need to copy (or create links of) the files
   in the directory ``/usr/local/share/gecode/mznlib`` into the
   directory ``/usr/local/share/minizinc/gecode``.
   ``cd /usr/local/share   sudo mkdir minizinc/gecode   sudo cp gecode/mznlib/* minizinc/gecode/``

-  The function ``pymzn.dzn`` arises a ``RecursionError`` when given a
   ``numpy.mat`` object as input. This problem arises because the
   iteration with ``numpy.mat`` behaves differently than
   ``numpy.ndarray`` or built-in ``list``. The simplest solution is to
   convert the ``numpy.mat`` into a ``numpy.ndarray``:
   ``matrix_array = np.asarray(matrix)``

Maintainers
-----------

`Paolo Dragone <http://paolodragone.com>`__, University of Trento
