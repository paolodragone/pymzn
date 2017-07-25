Implementation details
======================

This page describes the internal behavior of PyMzn. It is useful to understand
how problems are solved, serialization is ensured, and models are parsed.

Model flattening
----------------
The model flattening is carried out by the ``pymzn.mzn2fzn`` function
(in pymzn/mzn/minizinc.py) which in turn executes the MiniZinc *mzn2fzn*
utility to compile a MiniZinc model into a FlatZinc one.
The model flattening takes place exclusively through files. While
there is the possibility of executing the *mzn2fzn* writing the input model on
the standard input, it is rather inconvenient since it excludes the possibility
of providing inline data and dzn files.

Solver classes
--------------
To interface PyMzn to a solver, it needs a wrapper class that implements a
`solve` function, which takes the solver's arguments as input, executes the
solver with the provided arguments and the given MiniZinc/FlatZinc model and
returns the solution stream as output.  An example of that is the
``pymzn.Gecode`` class, which wraps the Gecode solver and implementes the
`solve` function by calling the *mzn-gecode* or *fzn-gecode* commands of Gecode.
To the time of writing, PyMzn supports Gecode, Opturion, OptiMathSat and Gurobi,
while the definition of additional solver classes is left to the user or to
future development.

Solution output stream
----------------------
The solution output stream provided by the solver `solve` implementation can
then be passed to the ``pymzn.solns2out`` function, which wraps the MiniZinc
*solns2out* utility. The ``pymzn.solns2out`` function takes as input the
solution stream and the ozn file returned by the ``pymzn.mzn2fzn`` function and
outputs a stream of solutions encoded in the format specified in the ozn file,
i.e. the format from the output statement in the model.

Solution parsing
----------------
When using the ``pymzn.minizinc`` function, the solutions are automatically
parsed into Python objects (if using ``output_mode='dict'``). This is carried out
by dropping the output statement of the original model and parsing either the
json or the dzn output of the solver. The original model file is isolated from
the new model file, as specified in the next section.

Thread safety
-------------
Some of the goals of PyMzn are to provide inline problem specification,
solution parsing, isolation of the solving instances and dynamic modelling.
These problems arise when one has a sequence of instances of a problem to
solve, possibly in parallel. To automatically ensure isolation of
the original problem from the solving instance, the ``pymzn.minizinc`` function
always compiles a new model file in a temporary file that is deleated right
after the problem has been successfully solved. If the paramenter `keep` is
`True`, then the temporary file is written into the folder containing the .mzn
file or the working directory if a model string is provided. In case of error,
the script that caused it is not deleated, even if `keep=False`. Writing the
models to temporary files ensures isolation of the solving instances and thus
thread safety.

