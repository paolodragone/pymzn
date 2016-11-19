Install
=======

PyMzn can be installed via Pip:::

    pip3 install pymzn

or from the source code:::

    python3 setup.py install

Currently, PyMzn is developed and maintained in Python v3.5 with a
porting to Python v2.7 at every release (the python2 branch does not contain
the most recent changes).

PyMzn requires some additional software to be installed on your system
before you can use it properly, namely:

* The `libminizinc library <https://github.com/MiniZinc/libminizinc>`__;
* A CSP solver compatible with the FlatZinc encoding, e.g. `Gecode <http://www.gecode.org>`__.


Install libminizinc
-------------------

The latest release of libminizinc can be found here:

    `<https://github.com/MiniZinc/libminizinc/releases/latest>`__

Download and install the package on your system. After that you should insert
the libminizinc binary path into the PATH environment variable, or alternatively
you can tell PyMzn's where to find the MiniZinc binaries
(see `Configuration <config.html>`__).

Install Gecode
--------------

The next step is to install a CSP solver compatible with FlatZinc. You
can use any solver you like, but the default one for PyMzn is
`Gecode <http://www.gecode.org>`__. If you use the Gecode solver, PyMzn will
work out-of-the-box, otherwise it will need some little configuration (see the
`Solvers <reference/solvers/>`__ section).

To install Gecode, we recommend you to download and compile the source code,
since binary packages are usually less frequently updated.
The Gecode source code can be downloaded from:

    `<http://www.gecode.org/download/>`__

Instructions on how to compile and install are found in the source package.
After installation, either put the Gecode binary directory into the PATH
variable, or configure PyMzn accordingly.

