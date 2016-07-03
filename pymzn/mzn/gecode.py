import logging

from pymzn.binary import command, run, BinaryRuntimeError


def fzn_gecode(fzn_file, *, time=0, parallel=1, n_solns=-1, seed=0,
               fzn_gecode_cmd='fzn-gecode', suppress_segfault=False,
               restart=None, restart_base=None, restart_scale=None):
    """
    Solves a constrained optimization problem using the Gecode solver,
    provided a .fzn input problem file.

    :param str fzn_file: The path to the fzn file containing the problem to
                         be solved
    :param str fzn_gecode_cmd: The command to call to execute the fzn-gecode
                               program; defaults to 'fzn-gecode', assuming
                               the program is the PATH
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
    :return: A binary string (bytes) containing the solution output stream
             of the execution of Gecode on the specified problem; it can be
             directly be given to the function solns2out or it can be read
             as a string using `out.decode('ascii')`
    :rtype: str
    """
    log = logging.getLogger(__name__)
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

    log.debug('Calling %s with arguments: %s', fzn_gecode_cmd, args)
    cmd = command(fzn_gecode_cmd, args)

    try:
        solns = run(cmd)
    except BinaryRuntimeError as bin_err:
        err_msg = bin_err.err_msg
        if (suppress_segfault and len(bin_err.out) > 0 and
                err_msg.startswith('Segmentation fault')):
            log.warning('Gecode returned error code {} (segmentation '
                        'fault) but a solution was found and returned '
                        '(suppress_segfault=True).'.format(bin_err.ret))
            solns = bin_err.out
        else:
            log.exception('Gecode returned error code {} '
                          '(segmentation fault).'.format(bin_err.ret))
            raise bin_err
    return solns
