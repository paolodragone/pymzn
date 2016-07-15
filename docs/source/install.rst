Install
=======

PyMzn can be installed via Pip:
::

    pip3 install pymzn

or from the source code:
::

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

While you can install any bundled MiniZinc package, the minimal
requirement to use PyMzn is to install the libminizinc library. The source
code of libminizinc is available at:

    `<https://github.com/MiniZinc/libminizinc/archive/master.zip>`__

Instructions on how to compile and install libminizinc are provided in the
source code. If you install libminizinc in a location different from the
default one, then it is strongly recommended to insert the libminizinc
binary path into the PATH environment variable, in order to avoid to
configure it in PyMzn at each use (see the
`Configuration <config.html>`__ section).

Install Gecode
--------------

The next step is to install a CSP solver compatible with FlatZinc. You
can use any solver you like, but the default one for PyMzn is
`Gecode <http://www.gecode.org>`__. If you use the Gecode solver, PyMzn will
work out-of-the-box, otherwise it will need some little configuration (see the
`Solvers <reference/solvers/>`__ section).

To install Gecode v4.4.0, we recommend you to download and compile the
source code, since binary packages are usually less frequently updated.
The Gecode source code can be downloaded from:

    `<http://www.gecode.org/download/gecode-4.4.0.tar.gz>`__

Instructions on how to compile and install are found in the source package.
Again, it is recommended to either install in the default location otherwise
to put the binary path of gecode into the PATH variable.
