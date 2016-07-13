Install
=======

PyMzn requires some additional software to be installed on your system
before you can use it properly, namely:

* The libminizinc library;
* A CSP solver compatible with the FlatZinc encoding.

Install libminizinc
-------------------

While you can install any bundled MiniZinc package, the minimal
requirement to use PyMzn is to install the libminizinc library. The source
code of libminizinc is available on `GitHub <https://github.com/MiniZinc/libminizinc/archive/master.zip>`__.
Instructions on how to compile and install libminizinc are provided in the
source code. If you install libminizinc in a location different from the
default one, then it is strongly recommended to insert the libminizinc
binary path into the PATH environment variable, in order to avoid to
configure it in PyMzn at each use.

Install Gecode
--------------

The next step is to install a CSP solver compatible with FlatZinc. You
can use any solver you like, but the default one for PyMzn is Gecode. If
you use Gecode as solver, PyMzn will work out-of-the-box, otherwise it
will need some little configuration (more on this in section `Additional
configuration <#config>`__).

To install Gecode v4.4.0, we recommend you to download and compile the
source code, since binary packages are usually less frequently updated.
The source code can be downloaded from the `Gecode website <http://www.gecode.org/download/gecode-4.4.0.tar.gz>`__.
Instruction on how to compile and install are found in the source package.
Again, it is recommended to either install in the default location otherwise
to put the binary path of gecode into the PATH variable.

Install PyMzn
-------------

After those preliminary steps, you can install PyMzn by either download
the source code from the
`GitHub <https://github.com/paolodragone/PyMzn>`__ repository and
include it in your project or install it through Pip:

::

    pip3 install pymzn

Adjust the version of Pip according to the python version you want to
use.