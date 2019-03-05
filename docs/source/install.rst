Install
=======

PyMzn can be installed via Pip::

    pip install pymzn


or from the source code available
on [GitHub](https://github.com/paolodragone/pymzn/releases/latest)::

    python setup.py install


Requirements
------------
PyMzn is developed and maintained in Python 3.5. Starting from version 0.18.0,
support for Python 2 and versions previous to 3.5 has been dropped (its just too
much work mainintaining them). Using the package `pymzn.aio` for concurrent
execution requires Python 3.6 (though it is optional).

PyMzn requires the MiniZinc toolkit to be installed on your machine. Starting
from PyMzn 0.18.0, the minimum MiniZinc version required is the 2.2.0. If you
need to work with previous versions of MiniZinc, PyMzn 0.17.1 should work fine.

The easiest way to install MiniZinc is to download the
`MiniZincIDE <https://github.com/MiniZinc/MiniZincIDE>`__ package, which
contains both the MiniZinc binaries and several solvers. After downloading the
package, make sure the `minizinc` executable is visible to PyMzn either by
setting the `PATH` environment variable or by configuring it using the
`pymzn.config` module.


Optional dependencies
---------------------

PyMzn offers the possibility of using `Jinja2
<http://jinja.pocoo.org/docs/intro/#installation>`__ syntax for templating
MiniZinc code (see `Templates <reference/templates>`__). To use templates you
need to install Jinja2. You can do that via Pip::

    pip install Jinja2

Check out Jinja's `installation
<http://jinja.pocoo.org/docs/intro/#installation>` for details.

To be able to set custom configuration for PyMzn (see `Configuration
<reference/configuration>`__) you need to install the `PyYAML
<https://pyyaml.org/wiki/PyYAML>`__ and `appdirs
<https://github.com/ActiveState/appdirs>`__ packages::

    pip install pyyaml appdirs


Install additional solvers
--------------------------

Starting from version 0.18.0, PyMzn interfaces directly with the `minizinc`
executable, which has now its own procedure for interfacing with installed
solvers. For more detailed information follow this `guide
<https://www.minizinc.org/doc-2.2.3/en/command_line.html#adding-solvers>`__ from
the MiniZinc user manual. Generally, any solver available to the `minizinc`
executable will be available to PyMzn as well. You can check which solvers are
installed by running the command::

    minizinc --solvers

For MiniZinc versions prior to the 2.2.0 and PyMzn versions prior to the 0.18.0,
you will need to install the solver and make sure that the path of the
executable associated with the solver is present in the `PATH` environment
variable.
