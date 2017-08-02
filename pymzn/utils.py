
import os
import time
import signal
import logging
import subprocess


def run(args, stdin=None):
    """Executes a command and waits for the result.

    It is also possible to interrupt the execution of the command with CTRL+C on
    the shell terminal (only in single thread).

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
    log.debug('Executing command with args: {}'.format(args))

    sighdl = False
    try:
        sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, lambda *args: None)
        sighdl = True
    except ValueError:
        # Happens in multi-threading, in which case ignore
        pass

    start = time.time()
    with subprocess.Popen(args, bufsize=1, universal_newlines=True,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        try:
            out, err = process.communicate(stdin)
            ret = process.poll()
        except KeyboardInterrupt:
            process.kill()
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            out, err = process.communicate(stdin)
            ret = 0
        finally:
            if sighdl:
                signal.signal(signal.SIGINT, sigint)

    elapsed = time.time() - start
    log.debug('Done. Running time: {0:.2f} seconds'.format(elapsed))

    process = subprocess.CompletedProcess(args, ret, out, err)
    process.check_returncode()
    return process

