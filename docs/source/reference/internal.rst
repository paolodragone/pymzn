Implementation details
======================

This page describes the internal behavior of PyMzn. It is useful to understand
how problems are solved, serialization is ensured, and models are parsed.

Model flattening
----------------
The model flattening is carried out by the ``pymzn.mzn2fzn`` function
(in pymzn/_mzn/_minizinc.py) which in turn executes the MiniZinc *mzn2fzn*
utility to compile a MiniZinc model into a FlatZinc one.
The model flattening takes place exclusively through files. While
there is the possibility of executing the *mzn2fzn* writing the input model on
the standard input, it is rather inconvenient since it excludes the possibility
of providing inline data and data (dzn) files. Moreover, by flattening a model
from command line, there would have been naming issues, because, as explained
in the section on `file naming <#file-naming>`__, PyMzn relies on a defined
set of naming rules to ensure isolation of the solving instances of a model.
The created files are left with the same name of the input file, as default of
the *mzn2fzn* utility. Given the `file naming <#file-naming>`__ conventions
and the internal behavior of the ``pymzn.minizinc`` function, the possibility
of specifying an output-base has been deemed as irrelevant and confusing, and
thus left out.

Solver proxy functions
----------------------
To interface PyMzn to a solver, it needs a proxy function which takes the
solver's arguments as input, executes the solver with the provided arguments
and the given FlatZinc model and returns the solution stream as output.
An example of that is the ``pymzn.gecode`` function, which wraps the
*fzn-gecode* command of Gecode. To the time of writing, PyMzn fully supports
Gecode and partially supports OptiMatSat, while the definition of additional
solver proxy functions is left to the user or to future development.

Solution output stream
----------------------
The solution output stream is provided by the solver proxy function which can
then be passed to the ``pymzn.solns2out`` function, which wraps the MiniZinc
*solns2out* utility. The ``pymzn.solns2out`` function takes as input the
solution stream and the ozn file returned by the ``pymzn.mzn2fzn`` function
and outputs a list of solutions encoded in the format specified in the ozn
file, i.e. the format from the output statement in the model.

Solution parsing
----------------
When using the ``pymzn.minizinc`` function, the solutions are automatically
parsed into Python objects (unless specified otherwise). This is carried out
by dropping the output statement of the original model and inserting a new
output statement which encodes the output variables into dzn format. The
original model file is isolated from the new model file, as specified in the
`File naming <#file-naming>`__ section.


File naming
-----------
Some of the objectives of PyMzn are to provide inline problem specification,
solution parsing, isolation of the solving instances and dynamic modelling.
These problems arise when one has a sequence of instances of a problem to
solve, possibly in parallel. To be able to ensure automatically isolation of
the original problem from the solving instance, the ``pymzn.minizinc`` function
always compiles a new model file with a *_n* appended to the name. Here *n* is
0 if the serialization is not activated, otherwise *n* is an increasing
natural number starting from 1. The counter is an instance of
``itertools.count()``, which is provably thread-safe, thereby ensuring
isolation of solving instances running in parallel.
