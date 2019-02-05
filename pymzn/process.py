"""process.py

This package implements the `Process` class, a helper class that wraps
`subprocess.Popen` and make it safe to use.
"""

import os

from time import monotonic as _time
from subprocess import Popen, PIPE, TimeoutExpired, CalledProcessError


__all__ = ['Process', 'run']


class Process:
    """Wrapper for an external process.

    Usable to run a synchronous process.

    Parameters
    ----------
    args : [str]
        The command line arguments to execute. Same as for `subprocess.Popen`
        (with `shell=False`).

    Attributes
    ----------
    returncode : int or None
        The returncode of the process. While the process has not finished the
        returncode is None. After the process is finished, the returncode is
        retrieved as by `Popen.poll()`.
    stdout_data : str or bytes
        The content of the standard output of the process after the execution.
    stderr_data : str or bytes
        The content of the standard error of the process after the execution.
    expired : bool
        Whether the process was terminated because the timeout expired.
    interrupted : bool
        Whether the process was interrupted by a KeyboardInterruption.
    started : bool
        Whether the process has started.
    completed : bool
        Whether the process was completed without errors.
    runtime : float
        The running time in seconds.
    """
    def __init__(self, args):
        self.args = args
        self.returncode = None
        self.timeout = None
        self.stdout_data = None
        self.stderr_data = None
        self.expired = False
        self.interrupted = False
        self._start = None
        self._end = None
        self._process = None

    @property
    def started(self):
        return self._process is not None

    @property
    def completed(self):
        return self.returncode == 0

    @property
    def runtime(self):
        if not self._start:
            return 0.0
        end = self._end or _time()
        return end - self._start

    def _check_started(self):
        if self.started:
            raise RuntimeError('Process already started')

    def run(self, input=None, timeout=None):
        """Run the process synchronously.

        Parameters
        ----------
        input : str or bytes or None
            The content to for the input stream of the process.
        timeout : float or None
            The timeout for the process. None means no timeout.
        """
        self._check_started()
        popenkwargs = {'bufsize': 1, 'universal_newlines': True,
                       'stdin': PIPE, 'stdout': PIPE, 'stderr': PIPE}
        if os.name == 'nt':
            popenkwargs['shell'] = True
        self.timeout = timeout
        self._start = _time()
        with Popen(self.args, **popenkwargs) as self._process:
            try:
                stdout, stderr = self._process.communicate(input, timeout)
                self.stdout_data, self.stderr_data = stdout, stderr
            except KeyboardInterrupt:
                self._process.kill()
                self._process.wait()
                self.interrupted = True
            except TimeoutExpired:
                self._process.kill()
                stdout, stderr = self._process.communicate()
                self.stdout_data, self.stderr_data = stdout, stderr
                self.expired = True
                raise TimeoutExpired(self.args, timeout, stdout, stderr)
            except:
                self._process.kill()
                self._process.wait()
                raise
            finally:
                self._end = _time()
                self.returncode = retcode = self._process.poll()
                if not (self.expired or self.interrupted) and self.returncode:
                    stdout, stderr = self.stdout_data, self.stderr_data
                    raise CalledProcessError(retcode, self.args, stdout, stderr)
        return self


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


def run_process(*args, input=None):
    shell = os.name == 'nt'
    start_time = _time()
    cp = subprocess.run(
        args, input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=shell, bufsize=1, universal_newlines=True
    )
    end_time = _time()
    return CompletedProcessWrapper(cp, start_time, end_time)


def run(*args, input=None):
    proc = run_process(*args, input=input)
    return proc.stdout_data.decode('utf-8')

