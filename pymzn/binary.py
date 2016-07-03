import collections.abc
import logging
import numbers
import subprocess


def command(path, args):
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
    cmd = [path]
    for arg in args:
        if isinstance(arg, str):
            cmd.append(arg)
        elif isinstance(arg, numbers.Number):
            cmd.append(str(arg))
        elif isinstance(arg, collections.abc.Iterable) and len(arg) == 2:
            k, v = arg
            if isinstance(k, str) and isinstance(v, (str, numbers.Number)):
                cmd.append(str(k))
                cmd.append(str(v))
            else:
                raise ValueError('Invalid argument: {}'.format(arg), arg)
        else:
            raise TypeError('Invalid argument: {}'.format(arg), arg)
    return ' '.join(cmd)


def run(cmd, stdin=None):
    """
    Executes a shell command and waits for the result.

    :param str cmd: The command string to be executed, as returned from the
                    command function.
    :param str stdin: String containing the input stream to pass to
                      the command
    :return: A string containing the output stream of the command
    :rtype: str
    """
    log = logging.getLogger(__name__)
    log.debug('Executing command: %s', cmd, extra={'stdin': stdin})
    proc = subprocess.Popen(cmd, shell=True, bufsize=1,
                            universal_newlines=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            # Still not sure if needed, without it kills the
                            #  subprocess after killing the parent,
                            # but I can't kill it from inside the program
                            # (which I don't need anymore though)
                            # preexec_fn=os.setsid
                            )
    out, err = proc.communicate(input=stdin)
    ret = proc.wait()

    if ret != 0:
        raise BinaryRuntimeError(cmd, ret, out, err)

    return out


def stream(cmd, stdin=None):
    """
    Executes a shell command and generates lines of output without waiting
    for it to finish.

    :param str cmd: The command string to be executed, as returned from the
                    command function.
    :param str stdin: Input stream to pass to the command
    :return: A generator containing the lines in the output stream
             of the command
    :rtype: generator of str
    """
    log = logging.getLogger(__name__)
    log.debug('Executing streaming command: %s', cmd, extra={'stdin': stdin})
    proc = subprocess.Popen(cmd, shell=True, bufsize=1,
                            universal_newlines=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            # Still not sure if needed, without it kills the
                            #  subprocess after killing the parent,
                            # but I can't kill it from inside the program
                            # (which I don't need anymore though)
                            # preexec_fn=os.setsid
                            )
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
    if ret != 0:
        raise BinaryRuntimeError(cmd, ret, out, err)


class BinaryRuntimeError(RuntimeError):
    """
        Exception for errors returned while executing a command.
    """

    def __init__(self, cmd, ret, out, err):
        """
        :param cmd: The command that generated the error
        :param ret: The code returned by the execution of cmd
        :param out: The output stream returned by the execution of cmd
        :param err: The error stream returned by the execution of cmd
        """
        self.cmd = cmd
        self.ret = ret
        self.out = out
        self.err = err
        msg = 'An error occurred while executing the command: {}\n{}'
        super().__init__(msg.format(self.cmd, self.err))
