
from __future__ import with_statement
from __future__ import absolute_import
import os
import time
import signal
import logging
import subprocess


class CompletedProcess(object):
    """A process that has finished running.
    This is returned by run().
    Attributes:
      args: The list or str args passed to run().
      returncode: The exit code of the process, negative for signals.
      stdout: The standard output (None if not captured).
      stderr: The standard error (None if not captured).
    """
    def __init__(self, args, returncode, stdout=None, stderr=None):
        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self):
        args = ['args={!r}'.format(self.args),
                'returncode={!r}'.format(self.returncode)]
        if self.stdout is not None:
            args.append('stdout={!r}'.format(self.stdout))
        if self.stderr is not None:
            args.append('stderr={!r}'.format(self.stderr))
        return "{}({})".format(type(self).__name__, ', '.join(args))

    def check_returncode(self):
        """Raise CalledProcessError if the exit code is non-zero."""
        if self.returncode:
            raise subprocess.CalledProcessError(self.returncode, self.args, self.stderr)


def run(args, stdin=None):
    u"""Executes a command and waits for the result.

    It is also possible to interrupt the execution of the command with CTRL+C on
    the shell terminal.

    Parameters
    ----------
    args : list
        The list of arguments for the program to execute. Arguments should be
        formatted as for the ``subprocess.Popen`` constructor.
    stdin : str or bytes
        String or bytes containing the input stream for the process.

    Returns
    -------
    CompletedProcess
        An instance of CompletedProcess containing the information about
        the executed process, including stdout, stderr and running time.

    Raises
    ------
    CalledProcessError
        When the process returns an error.
    """
    log = logging.getLogger(__name__)
    log.debug(u'Executing command with args: {}'.format(args))
    start = time.time()
    sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda *args: None)
    process = subprocess.Popen(args, bufsize=1, universal_newlines=True,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    try:
        out, err = process.communicate(stdin)
        ret = process.poll()
    except KeyboardInterrupt:
        process.kill()
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        out, err = process.communicate(stdin)
        ret = 0
    finally:
        signal.signal(signal.SIGINT, sigint)
    elapsed = time.time() - start
    log.debug(u'Done. Running time: {0:.2f} seconds'.format(elapsed))
    process = CompletedProcess(args, ret, out, err)
    process.check_returncode()
    return process

