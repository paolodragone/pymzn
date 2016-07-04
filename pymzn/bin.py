import collections.abc
import logging
import numbers
import subprocess


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


def run(arg, stdin=None):
    """
    Executes a shell command and waits for the result.

    :param str arg: The command string to be executed, as returned from the
                    cmd function.
    :param str stdin: String containing the input stream to pass to
                      the command
    :return: A string containing the output stream of the command
    :rtype: str
    """
    log = logging.getLogger(__name__)

    if isinstance(arg, list):
        arg = cmd(arg[0], arg[1:])

    log.debug('Executing command: %s', arg, extra={'stdin': stdin})
    proc = subprocess.run(arg, input=stdin, shell=True, bufsize=1,
                          universal_newlines=True,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    proc.check_returncode()
    return proc.stdout


def stream(arg, stdin=None):
    """
    Executes a shell command and generates lines of output without waiting
    for it to finish.

    :param str arg: The command string to be executed, as returned from the
                    cmd function.
    :param str stdin: Input stream to pass to the command
    :return: A generator containing the lines in the output stream
             of the command
    :rtype: generator of str
    """
    log = logging.getLogger(__name__)
    log.debug('Executing streaming command: %s', arg, extra={'stdin': stdin})
    proc = subprocess.Popen(arg, shell=True, bufsize=1,
                            universal_newlines=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if stdin:
        proc.stdin.write(stdin)
        proc.stdin.close()

    out = []
    for line in proc.stdout:
        out.append(line)
        yield line
    out = ''.join(out)
    err = proc.stderr.read()

    ret = proc.wait()
    if ret:
        raise subprocess.CalledProcessError(ret, arg, out, err)
