"""process.py

This package provides utilities for running synchronous external processes.
"""

import os
import subprocess

from time import monotonic as _time


__all__ = ['run_process']


class CompletedProcessWrapper:

    def Stream:

        def __init__(self, proc, transport=1):
            self._proc = proc
            self._transport = transport

        def readlines(self):
            if self._transport == 1:
                yield from self._proc.stdout_data.splitlines()
            else:
                yield from self._proc.stderr_data.splitlines()

    def __init__(self, proc, start_time, end_time):
        self._proc = proc
        self.stdout_stream = CompletedProcessWrapper.Stream(self, 1)
        self.stderr_stream = CompletedProcessWrapper.Stream(self, 2)
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

    @property
    def stdout_data(self):
        return self.stdout_stream

    @property
    def stderr_data(self):
        return self.stderr_stream


def run_process(*args, input=None):
    shell = os.name == 'nt'
    start_time = _time()
    cp = subprocess.run(
        args, input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=shell, bufsize=1, universal_newlines=True
    )
    end_time = _time()
    return CompletedProcessWrapper(cp, start_time, end_time)

