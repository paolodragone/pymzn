import os
import subprocess

# TODO: Document everything


def command(path, args):
    cmd = [path]
    for arg in args:
        if isinstance(arg, str):
            cmd.append(arg)
        elif isinstance(arg, (int, float)):
            cmd.append(str(arg))
        elif isinstance(arg, (tuple, list)) and len(arg) == 2:
            k, v = arg
            cmd.append(k)
            if isinstance(v, (str, int, float)):
                cmd.append(str(v))
        else:
            msg = 'Argument type not supported: {} [{}]'
            raise RuntimeError(msg.format(arg, type(arg)))
    return ' '.join(cmd)


def run(cmd, cmd_in=None) -> bytes:
    """
    Executes a shell command and waits for the result.

    :param str cmd:
    :param cmd_in: Input stream to pass to the command
    :return: The output stream of the command
    """

    pipe = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = pipe.communicate(input=cmd_in)
    ret = pipe.wait()

    if ret != 0:
        raise CommandRuntimeError(cmd, ret, out, err)

    return out


class CommandRuntimeError(RuntimeError):
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
        self.err_msg = err.decode('utf-8')
        msg = 'An error occurred while executing the command: {}\n{}'
        msg = msg.format(self.cmd, self.err_msg)
        super().__init__(msg)
