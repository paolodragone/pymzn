"""


If you want to specify custom paths to the MiniZinc or Gecode binaries
you can set their values through the ``pymzn.config`` module.

::

    import pymzn.config

    pymzn.config.mzn2fzn_cmd = path/to/mzn2fzn
    pymzn.config.solns2out_cmd = path/to/solns2out
    pymzn.config.gecode_cmd = path/to/fzn-gecode

These settings persist throughout the execution of your application. The
``pymzn.config`` module provides access to all the static settings of
PyMzn.

The configuration properties provided by ``pymzn.config`` are:

 * **mzn2fzn_cmd**: Path to the MiniZinc *mzn2fzn* utility command executable;
 * **solns2out_cmd**: Path to the MiniZinc *solns2out* utility command executable;
 * **gecode_cmd**: Path to the Gecode *fzn-gecode* utility command executable;
 * **optimatsat_cmd**: Path to the OptiMatSat *optimatsat* utility command executable;
 * **cmd_arg_limit**: The limit of characters for command line arguments;
   This property is used to decide whether to provide inline data as a shell
   argument to mzn2fzn or to write it automatically on a dzn file if the limit
   is exceeded.

PyMzn can also be set to print debugging messages on standard output
via:

::

    pymzn.debug()

This function is meant to be used in interactive sessions or in
applications that do not configure the ``logging`` library. If you
configure the ``logging`` library in your application, then PyMzn will
be affected as well. The logging level in PyMzn is always ``DEBUG``. To
disable debugging messages you can then call:

::

    pymzn.debug(False)

"""
import os.path


class _Config(object):

    def __init__(self):
        self._mzn2fzn_cmd = 'mzn2fzn'
        self._solns2out_cmd = 'solns2out'
        self._gecode_cmd = 'fzn-gecode'
        self._optimatsat_cmd = 'optimatsat'
        self._cmd_arg_limit = 2048

    @property
    def mzn2fzn_cmd(self):
        return self._mzn2fzn_cmd

    @mzn2fzn_cmd.setter
    def mzn2fzn_cmd(self, cmd):
        if os.path.exists(cmd):
            self._mzn2fzn_cmd = cmd
        else:
            raise ValueError('The given file does not exist: {}'.format(cmd))

    @property
    def solns2out_cmd(self):
        return self._solns2out_cmd

    @solns2out_cmd.setter
    def solns2out_cmd(self, cmd):
        if os.path.exists(cmd):
            self._solns2out_cmd = cmd
        else:
            raise ValueError('The given file does not exist: {}'.format(cmd))

    @property
    def gecode_cmd(self):
        return self._gecode_cmd

    @gecode_cmd.setter
    def gecode_cmd(self, cmd):
        if os.path.exists(cmd):
            self._gecode_cmd = cmd
        else:
            raise ValueError('The given file does not exist: {}'.format(cmd))

    @property
    def optimatsat_cmd(self):
        return self._optimatsat_cmd

    @optimatsat_cmd.setter
    def optimatsat_cmd(self, cmd):
        if os.path.exists(cmd):
            self._optimatsat_cmd = cmd
        else:
            raise ValueError('The given file does not exist: {}'.format(cmd))

    @property
    def cmd_arg_limit(self):
        return self._cmd_arg_limit

    @cmd_arg_limit.setter
    def cmd_arg_limit(self, limit):
        self._cmd_arg_limit = limit


_config = _Config()

# Package level configuration properties
mzn2fzn_cmd = _config.mzn2fzn_cmd
solns2out_cmd = _config.solns2out_cmd
gecode_cmd = _config.gecode_cmd
optimatsat_cmd = _config.optimatsat_cmd
cmd_arg_limit = _config.cmd_arg_limit
