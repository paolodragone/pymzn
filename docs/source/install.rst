Install
=======

PyMzn can be installed via Pip::

    pip install pymzn

or from the source code available
on `GitHub <https://github.com/paolodragone/pymzn/releases/latest>`__::

    python setup.py install

Currently, PyMzn is developed and maintained in Python 3.5 with a
porting to Python 2.7 at every release (the python2 branch does not always
contain the most recent changes).

PyMzn requires the MiniZinc toolkit to be installed on your machine, along with
at least one solver. The easiest way to install MiniZinc is to download the
`MiniZincIDE <https://github.com/MiniZinc/MiniZincIDE>`__ package, which
contains both the MiniZinc binaries and several solvers. After downloading the
package, make sure the executables are visible to PyMzn by either setting the
`PATH` environment variable or by configuring it using the `pymzn.config`
module.


Install libminizinc
-------------------

The latest release of the MiniZinc toolkit can be found here:

    `<https://github.com/MiniZinc/MiniZincIDE/releases/latest>`__

Download and install the package on your system. After that you should insert
the MiniZinc binary path into the PATH environment variable, or alternatively
you can configure PyMzn to find the MiniZinc binaries
(see `Configuration <config.html>`__).

