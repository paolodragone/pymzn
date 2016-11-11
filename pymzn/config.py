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
import yaml
import appdirs


_config = None
_modified = False

def _cfg_file():
    return os.path.join(appdirs.user_config_dir(__name__), 'config.yml')


def get(key, default=None):
    if _config is None:
        _config = {}
        cfg_file = _cfg_file()
        if os.path.isfile(cfg_file)
            with open(cfg_file) as f:
                config = yaml.load(f)
    return config.get(key, default)


def set(key, value):
    _config[key] = value
    _modified = True


def dump()
    if _modified:
        cfg_file = _cfg_file()
        with open(cfg_file, 'w') as f:
            yaml.dump(_config, f)
        _modified = False
