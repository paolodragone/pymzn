# -*- coding: utf-8 -*-
"""

PyMzn can be configured with custom executable paths and other variables.

To inspect the current value of a variable one can use the PyMzn executable, if
installed::

    $ pymzn config mzn2fzn

or equivalently::

    $ python3.5 -m pymzn config mzn2fzn

Similarly, to configure a variable::

    $ pymzn config mzn2fzn /path/to/mzn2fzn

or::

    $ python3.5 -m pymzn config mzn2fzn /path/to/mzn2fzn

The configuration of PyMzn is contained into a configuration file located in
the home directory of the current user. The exact path of the configuration file
is dependent on the operating system:

    * Linux: ~/.local/share/pymzn/config.yml
    * MacOS: ~/Library/Application Support/pymzn/config.yml
    * Windows: %APPDATA%\\Local\\pymzn\\config.yml

This is a YAML configuration file, which can be also manually modified.

PyMzn can also be configured programmatically using the module ``pymzn.config``.
For instance::

    import pymzn.config

    # config.set sets the variable only for the current execution
    pymzn.config.set('mzn2fzn', 'path/to/mzn2fzn')
    pymzn.config.set('solns2out', 'path/to/solns2out')

    # to make the changes persistent
    pymzn.dump()

The configurable properties used by PyMzn are the following:

 * **mzn2fzn**: Path to the *mzn2fzn* executable;
 * **solns2out**: Path to the *solns2out* executable;
 * **dzn_width**: The horizontal character limit for dzn files;
   This property is used to wrap long dzn statements when writing dzn files.
   This property is also used in the ``pymzn.minizinc`` function as a limit to
   decide whether to write the inline data into a file.

One can also configure custom properties to be used for custom solvers.


Debug
-----

PyMzn can also be set to print debugging messages on standard output via::

    pymzn.debug()

This function is meant to be used in interactive sessions or in
applications that do not configure the ``logging`` library. If you configure the
``logging`` library in your application, then PyMzn will print logging messages
as well. The logging level in PyMzn is always ``DEBUG``. To disable debugging
messages you can then call::

    pymzn.debug(False)

"""
import os
import yaml
import appdirs


_modified = False
_config = None
_defaults = {
        'mzn2fzn': 'mzn2fzn',
        'solns2out': 'solns2out',
        'dzn_width': 70
    }


def _cfg_file():
    return os.path.join(appdirs.user_config_dir(__name__), 'config.yml')


def get(key, default=None):
    """Get the value of a configuration variable.

    Parameters
    ----------
    key : str
        The key of the variable to retrieve.
    default
        The default value to return if the key does not exist.

    Returns
    -------
        The value associated to the key if the key exists, otherwise the default
        if provided.
    """
    global _config
    if _config is None:
        _config = {}
        cfg_file = _cfg_file()
        if os.path.isfile(cfg_file):
            with open(cfg_file) as f:
                _config = yaml.load(f)
    if not default:
        default = _defaults.get(key)
    return _config.get(key, default)


def set(key, value):
    """Set the value of configuration variable.

    Parameters
    ----------
    key : str
        The key of the variable to set.
    value
        The value to assign to the variable.
    """
    global _config
    global _modified
    _config[key] = value
    _modified = True


def dump():
    """Writes the changes to the configuration file."""
    global _config
    global _modified
    if _modified:
        cfg_file = _cfg_file()
        cfg_dir, __ = os.path.split(cfg_file)
        os.makedirs(cfg_dir, exist_ok=True)
        with open(cfg_file, 'w') as f:
            yaml.dump(_config, f)
        _modified = False

