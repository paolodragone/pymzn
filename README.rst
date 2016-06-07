PyMzn
=====

PyMzn is a python3 wrapper for the MiniZinc tools pipeline. It builds on
top the libminizinc library, which executables are called by this
library's utilities.

Install
-------

To install PyMzn you first need to download and compile libminizinc
from: https://github.com/MiniZinc/libminizinc/archive/master.zip
Instructions on how to compile libminizinc are provided in the package.
It is not necessary but strongly recommended to insert the path to the
folder containing the binaries of the libminizinc tools into the PATH
environment variable.

To use MiniZinc one needs a CSP solver installed. The default one
assumed by this library is Gecode, which you can download from this
page: http://www.gecode.org/download.html In principle you can use any
solver you like, provided it is compatible with MiniZinc.

After those preliminary steps you can install PyMzn by either download
the code and use it or install the library via Pip:

::

        pip3 install pymzn

Quick Start
-----------

First thing, you need a MiniZinc model encoding the problem to solve.
Here is a simple 0-1 knapsack problem encoded in MiniZinc:

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

Assuming you installed Gecode (the default solver supported by this
library), you can run minizinc through pymzn like this:

::

    import pymzn
    pymzn.minizinc('test.mzn')

If you want to use a different solver, please read the following
section.

If you didn't put the binaries of libminizinc into the PATH environment
variable, you need to specify this path using the ``bin_path`` argument:

::

    pymzn.minizinc('test.mzn', bin_path='path/to/libminizinc')

The returned value will be:

::

    [{'x': {3, 5}}]

The output of the ``minizinc`` function is a list of solutions. Each
solution is a dictionary containing the assignment of each variable to
its value. The assignments are key-value pairs where the key is a string
containing the name of the variable in the mzn file and the value is the
output value for that variable. Each output value is parsed and
transformed into an equivalent value using python structures, i.e.
integers are converted into python's integers, floats are converted into
python's floats, sets are converted into python's sets, arrays and
matrices are converted into python's lists and lists of lists. (NOTE:
this is the default behaviour, it only works if no output statement is
used in the minizinc model, more information about how to change it in
the Parsing section)

The ``pymzn`` module also provide the convenience function
``dict2array`` to convert the dict-based representation output by the
``parse_dzn`` function into an array-based representation more suitable
to represent vectors and matrices of numbers.

The behaviour of the ``minizinc`` function can be adjusted by passing
keywords arguments, which are explained in detail in the documentation.
There is an almost one-to-one match with command line arguments of the
libminizinc utilities.

For instance, you can pass data to the ``minizinc`` function in the form
of a dictionary of python objects, which are then converted in the right
dzn format and feed to the mzn2fzn utility (more information about this
in the following section).

::

    pymzn.minizinc('test.mzn', data={'n': 10})

Otherwise you can provide dzn files containing the data:

::

    pymzn.minizinc('test.mzn', dzn_files=['data1.dzn', 'data2.dzn'])

Or you can use both.

Solvers
-------

If you want to use a different solver other than Gecode, you first need
to make sure that it supports the MiniZinc interface. To solve your
model through PyMzn you need to provide a proxy function to handle the
command line interface of the solver, this is an example:

::

    import pymzn

    def solve(fzn_file, arg1=def_val1, arg2=def_val2):
        solver = 'path/to/solver'
        args = [solver, '-arg1', str(arg1), '-arg2', str(arg2), fzn_file]
        cmd = ' '.join(args)
        ret, out, err = pymzn.run(cmd)

        if ret != 0:
            raise Exception('Something went wrong:\n{}'.format(err))

        return out

Then you can run the ``minizinc`` function like this:

::

    pymzn.minizinc('test.mzn', fzn_cmd=solve, fzn_flags={'arg1':val1, 'arg2':val2})

Parsing
-------

The output stream of the solver is parsed by the ``solns2out`` function.
To parse the output one needs a specialized function. The default one is
the ``parse_dzn`` function. If no parsing function (``parse=None``) is
passed to the ``solns2out`` function then the raw output of the solver
is used as output solution stream. If a custom output statement is used
in the minizinc model, then an appropriate parsing function must be
provided as well.

Dzn data files
--------------

The PyMzn library also provides a set of methods to convert python
objects into dzn format.

::

    pymzn.dzn({'x': 2, 'y': {4, 6, 8}, 'z': [4.5, 1.3, 5.7]})

The ``dzn`` function gets a dictionary of python objects as input and
returns a list of variable declaration statements in dzn format.
Optionally, you can pass the path to a dzn file where to write the
statements.

::

    pymzn.dzn(data, fout='path/to/dzn')

The supported types of python objects are: \* String (str) \* Integer
(int) \* Float (float) \* Set (set of str, int of float) \* Array (list
of str, int, float or set) \* Matrix (list of lists of str, int, float
or set) [the inner lists must have the same length]

Maintainers
-----------

`Paolo Dragone <http://paolodragone.com>`__, University of Trento
