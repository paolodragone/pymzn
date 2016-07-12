import logging
from subprocess import CalledProcessError

import pymzn.config as config
from pymzn.bin import cmd, run


__all__ = ['gecode', 'optimatsat', 'solve']


def gecode(fzn_file, *, time=0, parallel=1, n_solns=-1, seed=0, restart=None,
           restart_base=None, restart_scale=None, suppress_segfault=False):
    """
    Solves a constrained optimization problem using the Gecode solver,
    provided a .fzn input problem file.

    :param str fzn_file: The path to the fzn file containing the problem to
                         be solved
    :param int n_solns: The number of solutions to output (0 = all,
                        -1 = one/best); default is -1
    :param int parallel: The number of threads to use to solve the problem
                         (0 = #processing units); default is 1
    :param int time: The time cutoff in milliseconds, after which the
                     execution is truncated and the best solution so far is
                     returned, 0 means no time cutoff; default is 0
    :param int seed: random seed; default is 0
    :param str restart: restart sequence type; default is None
    :param str restart_base: base for geometric restart sequence; if None (
                             default) the default value of Gecode is used,
                             which is 1.5
    :param str restart_scale: scale factor for restart sequence; if None (
                              default) the default value of Gecode is used,
                              which is 250
    :param bool suppress_segfault: whether to accept or not a solution
                                   returned when a segmentation fault has
                                   happened (this is unfortunately necessary
                                   sometimes due to some bugs in gecode).
    :return: A string containing the solution output stream of the execution
             of Gecode on the specified problem; it can be directly be given
             to the function solns2out to be transformed into output and
             then parsed
    :rtype: str
    """
    args = []
    if n_solns >= 0:
        args.append(('-n', n_solns))
    if parallel != 1:
        args.append(('-p', parallel))
    if time > 0:
        args.append(('-time', time))
    if seed != 0:
        args.append(('-r', seed))
    if restart:
        args.append(('-restart', restart))
    if restart_base:
        args.append(('-restart-base', restart_base))
    if restart_scale:
        args.append(('-restart-scale', restart_scale))
    args.append(fzn_file)

    log = logging.getLogger(__name__)
    log.debug('Calling %s with arguments: %s', config.gecode_cmd, args)

    try:
        solns = run(cmd(config.gecode_cmd, args))
    except CalledProcessError as err:
        if (suppress_segfault and len(err.stdout) > 0 and
                err.stderr.startswith('Segmentation fault')):
            log.warning('Gecode returned error code {} (segmentation '
                        'fault) but a solution was found and returned '
                        '(suppress_segfault=True).'.format(err.returncode))
            solns = err.stdout
        else:
            log.exception(err.stderr)
            raise RuntimeError(err.stderr) from err
    return solns


def solve(fzn_file, solver_cmd=None):
    args = [fzn_file]

    log = logging.getLogger(__name__)
    log.debug('Calling %s with arguments: %s', solver_cmd, args)

    try:
        solns = run(cmd(solver_cmd, args))
    except CalledProcessError as err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr) from err
    return solns


def optimatsat(fzn_file):
    args = ['-input=fzn', fzn_file]

    log = logging.getLogger(__name__)
    log.debug('Calling %s with arguments: %s', config.optimatsat_cmd, args)

    try:
        solns = run(cmd(config.optimatsat_cmd, args))
    except CalledProcessError as err:
        log.exception(err.stderr)
        raise RuntimeError(err.stderr) from err
    return solns
