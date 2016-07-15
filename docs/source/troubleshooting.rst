Troubleshooting
===============

-  Gecode raises the following error at the first execution after the
   installation (on Linux):
   ::

       fzn-gecode: error while loading shared libraries: libgecodeflatzinc.so.41: cannot open shared object file: No such file or directory

   To solve this problem you need to set the environment variable
   ``LD_LIBRARY_PATH`` before running your Python script:
   ::

       export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib/

   or put the script into your ``~/.bashrc`` file and then run:
   ::

       source ~/.bashrc

-  Minizinc raises the following error when trying to include the gecode
   library with the ``-G gecode`` option (on Linux):
   ::

       Cannot access include directory /usr/local/bin/../share/minizinc/gecode/

   To solve this problem you need to copy (or create links of) the files
   in the directory ``/usr/local/share/gecode/mznlib`` into the
   directory ``/usr/local/share/minizinc/gecode``.
   ::

       cd /usr/local/share
       sudo mkdir minizinc/gecode
       sudo ln -s gecode/mznlib/* minizinc/gecode/

-  The function ``pymzn.dzn`` arises a ``RecursionError`` when given a
   ``numpy.mat`` object as input. This problem arises because the
   iteration with ``numpy.mat`` behaves differently than
   ``numpy.ndarray`` or built-in ``list``. The simplest solution is to
   convert the ``numpy.mat`` into a ``numpy.ndarray``:
   ::

       matrix_array = np.asarray(matrix)

