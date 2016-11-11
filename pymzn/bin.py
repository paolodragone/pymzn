"""
PyMzn wraps the MiniZinc tools by executing them with the ``subprocess.run``
function from the standard library. The process of running a executable,
checking for errors and returning the output is carried out by the
``pymzn.bin.run`` function, which takes as input either a string or a list of
arguments to pass to the ``pymzn.bin.cmd`` function.

The ``pymzn.bin.cmd`` can be used in this way:
::

    pymzn.bin.cmd('path/to/command', [5, '-f', '--flag2', ('--args1', 'val1'), ('--args2', 2)])

which will become:
::

    'path/to/command 5 -f --flag2 --args1 val1 --args2 2'

"""
import os
import time
import signal
import subprocess

from ._utils import get_logger


class TimedCompletedProcess(subprocess.CompletedProcess):
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
        if not self.expired:
            super().check_returncode()


def run(args, stdin=None, timeout=None):
    """
    Executes a shell command and waits for the result.

    :param str args: The command string to be executed, as returned from the
                    cmd function.
    :param str stdin: String containing the input stream to pass to
                      the command
    :return: A string containing the output stream of the command
    :rtype: str
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

