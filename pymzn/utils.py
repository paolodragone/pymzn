
import logging
import subprocess


""" Logging utilities """

class Message(object):
    def __init__(self, fmt, args):
        self.fmt = fmt
        self.args = args

    def __str__(self):
        return self.fmt.format(*self.args)


class BracesAdapter(logging.LoggerAdapter):
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})

    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):
            msg, kwargs = self.process(msg, kwargs)
            self.logger._log(level, Message(msg, args), (), **kwargs)


def get_logger(name):
    return BracesAdapter(logging.getLogger(name))



""" Binary utilities """

def run(args, stdin=None):
    """Executes a command and waits for the result.

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
    log = get_logger(__name__)
    log.debug('Executing command with args: {}', args)
    start = time.time()
    with subprocess.Popen(args, bufsize=1, universal_newlines=True,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        out, err = process.communicate(stdin)
        ret = process.poll()
    elapsed = time.time() - start
    log.debug('Done. Running time: {0:.2f} seconds'.format(elapsed))
    process = subprocess.CompletedProcess(args, ret, out, err)
    process.check_returncode()
    return process

