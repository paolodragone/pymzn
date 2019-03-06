"""\
This package provides utilities for running synchronous external processes.
"""

import os
import subprocess

from time import monotonic as _time


__all__ = ['run_process']


class CompletedProcessWrapper:

    def __init__(self, proc, start_time, end_time):
        self._proc = proc
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self):
        return repr(self._proc)

    @property
    def args(self):
        return self._proc.args

    @property
    def returncode(self):
        return self._proc.returncode

    @property
    def stdout_data(self):
        return self._proc.stdout

    @property
    def stderr_data(self):
        return self._proc.stderr

    def readlines(self):
        yield from self.stdout_data.splitlines()


def run_process(*args, input=None):
    """Run an external process.

    Parameters
    ----------
    *args : list of str
        The arguments to pass to the external process. The first argument should
        be the executable to call.
    input : str or bytes
        The input stream to supply to the extenal process.

    Return
    ------
        Object wrapping the executed process.
    """
    shell = os.name == 'nt'
    start_time = _time()
    cp = subprocess.run(
        args, input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=shell, bufsize=1, universal_newlines=True
    )
    end_time = _time()
    return CompletedProcessWrapper(cp, start_time, end_time)

