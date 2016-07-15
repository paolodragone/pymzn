Serialization
=============

Another important aspect that PyMzn addresses is the "isolation" of
solving instances of a problem. This problem arises when there are
multiple solving instances of the same problem file running in parallel.
This is especially important when the problems are continuously solved
in separate threads. PyMzn can be set to make sure that the instances do
not interfere with each other, by setting the argument
``serialize=True`` in the ``minizinc`` function. For instance:

::

    import threading

    solutions = {}

    def solve(n):
        solutions[n] = pymzn.minizinc('test.mzn', data={'n': n}, serialize=True)

    for n in range(10):
        threading.Thread(target=solve, args=(n,)).start()

Setting ``serialize=True`` in each solving instance will prevent all the
instances from interfering with each other.