# -*- coding: utf-8 -*-
"""Convenience module for running executables.

PyMzn executes the MiniZinc tools and the solvers with the functions
contained in the standard ``subprocess`` module. As a convenience method, PyMzn
provides the method ``pymzn.bin.run`` which takes the arguments of a binary
executable, as for the ``subprocess.Popen`` constructor. This method returns an
instance of ``pymzn.bin.TimedCompletedProcess``, a subclass of
``subprocess.CompletedProcess`` which contains also information about the
timeout.
"""
import os
import time
import signal
import subprocess

from ._utils import get_logger


class TimedCompletedProcess(subprocess.CompletedProcess):
    """Contains information about a completed process.

    An instance of this class is always returned by the ``pymzn.bin.run``
    method. This is a subclass of ``subprocess.CompletedProcess`` including
    additional information about running time and process timeout.

    Attributes
    ----------
    args : list or str
        The args passed to run().
    returncode : int
        The exit code of the process, negative for signals.
    time : float
        The running time in seconds.
    timeout : int or float
        The timeout given to the process.
    expired : bool
        Whether the time has expired and the process has been terminated before
        finishing.
    stdout : bytes
        The standard output (None if not captured).
    stderr : bytes
        The standard error (None if not captured).
    """
    def __init__(self, args, returncode, time, timeout=None, stdout=None,
                 stderr=None):
        super().__init__(args, returncode, stdout=stdout, stderr=stderr)
        self.time = time
        self.timeout = timeout
        self.expired = timeout and time >= timeout

    def __repr__(self):
        args = ['args={!r}'.format(self.args),
                'returncode={!r}'.format(self.returncode),
                'time={!r}'.format(self.time),
                'timeout={!r}'.format(self.timeout)]
        if self.stdout is not None:
            args.append('stdout={!r}'.format(self.stdout))
        if self.stderr is not None:
            args.append('stderr={!r}'.format(self.stderr))
        return "{}({})".format(type(self).__name__, ', '.join(args))

    def check_returncode(self):
        """Raise CalledProcessError if the exit code is non-zero and the time
        has not expired.
        """
        if not self.expired:
            super().check_returncode()


def run(args, stdin=None, timeout=None):
    """Executes a command and waits for the result.

    Parameters
    ----------
    args : list
        The list of arguments for the program to execute. Arguments should be
        formatted as for the ``subprocess.Popen`` constructor.
    stdin : str or bytes
        String or bytes containing the input stream for the process.
    timeout : int or float
        The timeout for the process in seconds.

    Returns
    -------
    TimedCompletedProcess
        An instance of TimedCompletedProcess containing the information about
        the executed process, including stdout, stderr and running time.

    Raises
    ------
    CalledProcessError
        When the process returns an error.
    """
    log = get_logger(__name__)
    log.debug('Executing command with args: {}', args)
    start = time.time()
    with subprocess.Popen(args, bufsize=1, universal_newlines=True,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          # preexec_fn not supported on windows, find a better
                          # solution, maybe this all works even without the
                          # line below
                          preexec_fn=os.setsid) as process:
        try:
            out, err = process.communicate(stdin, timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            out, err = process.communicate()
        ret = process.poll()
        end = time.time()
    elapsed = end - start
    log.debug('Done. Running time: {0:.2f} seconds'.format(elapsed))
    process = TimedCompletedProcess(args, ret, elapsed, timeout, out, err)
    process.check_returncode()
    return process

