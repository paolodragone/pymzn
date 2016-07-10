[PyMzn](https://github.com/paolodragone/PyMzn)
==============================================

PyMzn is a Python wrapper for the MiniZinc tool pipeline. <br/>
It is built on top of the libminizinc library (version 2.0) and provides a
number of off-the-shelf functions to readily solve problems encoded in
MiniZinc and parse the solutions into python objects.

Currently, PyMzn is developed and maintained in Python v3.5 with a porting to
Python v2.7 at every release (without the most recent changes).

Install
-------

PyMzn requires some additional software to be installed on your system before
you can use it properly, namely:
* The libminizinc library;
* A CSP solver compatible with the FlatZinc encoding.

### Install Libminizinc

While you can install any bundled MiniZinc package, the minimal requirement to
use PyMzn is to install the libminizinc library. You can download the source
code of libminizinc from:
<br/>
https://github.com/MiniZinc/libminizinc/archive/master.zip
<br/>
Instructions on how to compile and install libminizinc are provided in the
source code. If you install libminizinc in a location different from the
default one, then it is strongly recommended to insert the libminizinc binary
path into the PATH environment variable, in order to avoid to configure it in
PyMzn at each use.

### Install Gecode

The next step is to install a CSP solver compatible with FlatZinc. You can
use any solver you like, but the default one for PyMzn is Gecode. If you use
Gecode as solver, PyMzn will work out-of-the-box, otherwise it will need some
little configuration (more on this in section
[Additional configuration](#config)).

To install Gecode v4.4.0, we recommend you to download and compile the source
code, since binary packages are usually less frequently updated. The source
code is available at:
<br/>
http://www.gecode.org/download/gecode-4.4.0.tar.gz
<br/>
Instruction on how to compile and install are found in the source package.
Again, it is recommended to either install in the default location otherwise
to put the binary path of gecode into the PATH variable.

### Install PyMzn

After those preliminary steps, you can install PyMzn by either download the
source code from the [GitHub](https://github.com/paolodragone/PyMzn)
repository and include it in your project or install it through Pip:
```
pip3 install pymzn
```
Adjust the version of Pip according to the python version you want to use.

Quick Start
-----------

First, you need a MiniZinc model encoding the problem you want to solve. Here
is a simple 0-1 knapsack problem encoded with MiniZinc:
```
%% test.mzn %%

int: n = 5;
set of int: OBJ = 1..n;
int: capacity = 20;
array[OBJ] of int: profit = [10, 3, 9, 4, 8];
array[OBJ] of int: size = [14, 4, 10, 6, 9];

var set of OBJ: x;
constraint sum(i in x)(size[i]) <= capacity;
var int: obj = sum(i in x)(profit[i])
solve maximize obj;
```

You can solve the above problem using the PyMzn `minizinc` function:
```
import pymzn
pymzn.minizinc('test.mzn')
```
The result will be:
```
[{'x': {3, 5}}]
```
The `minizinc` function returns a list of solutions. The default behavior is
to evaluate the solutions into python objects. Solutions are dictionaries
containing variable assignments. The returned variables are, by default, the
'free' variables, i.e. those that do not depend on other variables.
If you are interested in the value of other variables for each solution you
can specify the `output_vars` argument:
```
pymzn.minizinc('test.mzn', output_vars=['x', 'obj'])
```
This will override the default behavior so, if you are still interested in
the default set of variables, you need to specify them as well.

The evaluation of the solutions by PyMzn uses an internal output
representation (actually dzn format) specified as an output statement that
overrides the one specified in the model if any (though the original output
statement in your model is left untouched, more details on how PyMzn works
internally are available in the documentation).

If you wish to override the default behavior and get as output strings
formatted with your original output statement you can use the `raw_output`
argument:
```
pymzn.minizinc('test.mzn', raw_output=True)
```
This will disable the automatic parsing, so the `output_vars` will be ignored
if specified.

### Data
It is possible to specify data (.dzn) files to the `minizinc` function as
additional positional arguments:
```
pymzn.minizinc('test.mzn', 'data1.dzn', 'data2.dzn')
```
It is also possible to specify additional data inline with the `minizinc`
function:
```
pymzn.minizinc('test.mzn', 'data1.dzn', 'data2.dzn', data={'n': 10, 'm': [1,3,5]})
```
With the `data` argument you can specify an assignment of variables that will
be automatically converted to dzn format with the `pymzn.dzn` function (more
details in the [Dzn files](#dzn) section).

### Solver's arguments
Usually, solvers provide arguments that can be used to modify their behavior.
You can specify arguments to pass to the solver as additional keyword
arguments in the `minizinc` function. For instance, using the argument `time`
for Gecode, it will set a time cut-off (in milliseconds) for the problem
solving.
```
pymzn.minizinc('test.mzn', time=30000)  # 30 seconds cut-off
```
Adding the `parallel` argument, you can specify how many threads should Gecode
use for the problem solving:
```
pymzn.minizinc('test.mzn', time=30000, parallel=0)  # 0 = number of available CPU cores
```
More details on available options are in the documentation.

<a name="config"></a>

Additional configuration
------------------------
If you want to specify custom paths to the MiniZinc or Gecode binaries you can
set their values through the `pymzn.config` module.
```
import pymzn.config

pymzn.config.mzn2fzn_cmd = path/to/mzn2fzn
pymzn.config.solns2out_cmd = path/to/solns2out
pymzn.config.gecode_cmd = path/to/fzn-gecode
```
These settings persist throughout the execution of your application.
The `pymzn.config` module provides access to all the static settings of PyMzn.

PyMzn can also be set to print debugging messages on standard output via:
```
pymzn.debug()
```
This function is meant to be used in interactive sessions or in applications
that do not configure the `logging` library. If you configure the `logging`
library in your application, then PyMzn will be affected as well. The logging
level in PyMzn is always `DEBUG`.
To disable debugging messages you can then call:
```
pymzn.debug(False)
```

<a name="solvers"></a>

Solvers
-------
If you want to use a different solver other than Gecode, you first need to
make sure that it supports the FlatZinc input.
To solve your model through PyMzn using the selected solver, you need to
use a proxy function.
PyMzn provides natively a number of solvers proxy functions. If the solver
your solver is not supported natively, you can use the generic proxy function
`pymzn.solve`:
```
pymzn.minizinc('test.mzn', fzn_fn=pymzn.solve, solver_cmd='path/to/solver')
```

If you want to provide additional arguments and flexibility to the solver, you
can define your own proxy function. Here is an example:
```
from pymzn.binary import cmd, run

def my_solver(fzn_file, arg1=def_val1, arg2=def_val2):
    solver = 'path/to/solver'
    args = [('-arg1', arg1), ('-arg2', arg2), fzn_file]
    return run(cmd(solver, args))
```
Then you can run the `minizinc` function like this:
```
pymzn.minizinc('test.mzn', fzn_cmd=fzn_solver, arg1=val1, arg2=val2)
```

<a name="dzn"></a>

Dzn files
----------------------
The PyMzn library also provides a set of methods to convert python objects
into dzn format.
```
pymzn.dzn({'a': 2, 'b': {4, 6}, 'c': {1, 2, 3}, 'd': {3: 4.5, 4: 1.3}, 'e': [[1, 2], [3, 4], [5, 6]]})
```
The `dzn` function gets a dictionary of python objects as input and returns
a list of variable declaration statements in dzn format.
For instance, the output of the previous example would be:
```
['a = 2;', 'b = {4, 6};', 'c = 1..3;', 'd = array1d(3..4, [4.5, 1.3]);', 'e = array2d(1..3, 1..2, [1, 2, 3, 4, 5, 6];']
```

Optionally, you can pass the path to a dzn file where to write the statements.
```
pymzn.dzn(data, fout='path/to/dzn')
```
The supported types of python objects are:
* String (str)
* Integer (int)
* Float (float)
* Set (set of str, int of float)
* Multi-dimensional arrays:
  * list of str, int, float or set; lists are converted into dzn arrays
  with index-set 1..len(list);
  * dict with int keys of str, int, float or set; dicts are converted into dzn
  arrays with index-set equal to the key-set of the dict, provided that it is a
  contiguous set;
  * nested combinations of the previous two, provided that the children of
  every node have the same index-set. The maximum depth is 6.

Serialization
-------------

Troubleshooting
---------------
* Gecode raises the following error at the first execution after the
  installation:
  ```
  fzn-gecode: error while loading shared libraries: libgecodeflatzinc.so.41: cannot open shared object file: No such file or directory
  ```
  To solve this problem you need to set the environment variable
  `LD_LIBRARY_PATH` before running your Python script:
  ```
  export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib/
  ```
  or put the script into your `~/.bashrc` file and then run:
  ```
  source ~/.bashrc
  ```

* Minizinc raises the following error when trying to include the gecode library
  with the `-G gecode` option:
  ```
  Cannot access include directory /usr/local/bin/../share/minizinc/gecode/
  ```
  To solve this problem you need to copy (or create links of) the files in the
  directory `/usr/local/share/gecode/mznlib` into the directory `/usr/local/share/minizinc/gecode`.
  ```
  cd /usr/local/share
  sudo mkdir minizinc/gecode
  sudo cp gecode/mznlib/* minizinc/gecode/
  ```

* The function `pymzn.dzn` arises a `RecursionError` when given a `numpy.mat`
  object as input. This problem arises because the iteration with `numpy.mat`
  behaves differently than `numpy.ndarray` or built-in `list`. The simplest
  solution is to convert the `numpy.mat` into a `numpy.ndarray`:
  ```
  matrix_array = np.asarray(matrix)
  ```

Maintainers
-----------

[Paolo Dragone](http://paolodragone.com), University of Trento
