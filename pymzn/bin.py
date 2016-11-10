"""
PyMzn wraps the MiniZinc tools by executing them with the ``subprocess.run``
function from the standard library. The process of running a executable,
checking for errors and returning the output is carried out by the
``pymzn.bin.run`` function, which takes as input either a string or a list of
arguments to pass to the ``pymzn.bin.cmd`` function.

The ``pymzn.bin.cmd`` can be used in this way:
::

    pymzn.bin.cmd('path/to/command', [5, '-f', '--flag2', ('--arg1', 'val1'), ('--arg2', 2)])

which will become:
::

    'path/to/command 5 -f --flag2 --arg1 val1 --arg2 2'

"""
import os
import time
import signal
import numbers
import subprocess
import collections.abc

from ._utils import get_logger


def run_cmd(path, args, stdin=None, timeout=None):
    return run(cmd(path, args), stdin=stdin, timeout=timeout)


def cmd(path, args):
    """
    Returns the command string from the path to the binary with the provided
    arguments.

    :param string path: The path to the binary file to be executed. If the
                        binary is in the PATH, then only the name is needed
    :param list args: A list of arguments to pass to the command. Supported
                      types of arguments are str, int, float and key-value
                      tuples
    :return: The string command
    :rtype: str
    """
    _cmd = [path]
    for arg in args:
        if isinstance(arg, str):
            _cmd.append(arg)
        elif isinstance(arg, numbers.Number):
            _cmd.append(str(arg))
        elif isinstance(arg, collections.abc.Iterable) and len(arg) == 2:
            k, v = arg
            if isinstance(k, str) and isinstance(v, (str, numbers.Number)):
                _cmd.append(str(k))
                _cmd.append(str(v))
            else:
                raise ValueError('Invalid argument: {}'.format(arg))
        else:
            raise TypeError('Invalid argument: {}'.format(arg))
    return ' '.join(_cmd)


def run(arg, stdin=None, timeout=None):
    """
    Executes a shell command and waits for the result.

    :param str arg: The command string to be executed, as returned from the
                    cmd function.
    :param str stdin: String containing the input stream to pass to
                      the command
    :return: A string containing the output stream of the command
    :rtype: str
    """
    log = get_logger(__name__)

    if isinstance(arg, list):
        arg = cmd(arg[0], arg[1:])

    log.debug('Executing command: %s', arg, extra={'stdin': stdin})
    start = time.time()
    proc = subprocess.Popen(arg, shell=True, bufsize=1,
                            universal_newlines=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            preexec_fn=os.setsid)
    try:
        out, err = proc.communicate(stdin, timeout=timeout)
        ret = proc.wait()
        if ret:
            raise RuntimeError(err)
    except subprocess.TimeoutExpired:
        proc.kill()
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        out, err = proc.communicate()
    end = time.time()
    log.debug('Done. Running time: {0:.2f} seconds'.format(end - start))
    return out

