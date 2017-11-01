# -*- coding: utf-8 -*-
"""

PyMzn can be configured with custom executable paths and other variables.
Configuration is done via the module ``pymzn.config``. For instance::

    import pymzn.config

    pymzn.config.set('mzn2fzn', 'path/to/mzn2fzn')
    pymzn.config.set('solns2out', 'path/to/solns2out')

The configurable properties used by PyMzn are the following:

 * **mzn2fzn**: Path to the *mzn2fzn* executable;
 * **solns2out**: Path to the *solns2out* executable;
 * **solver**: Solver instance to use when calling pymzn.minizinc;
 * **solver_args**: Arguments to pass to the solver when calling pymzn.minizinc;
 * **keep**: Overrides the keep flag of all minizinc and mzn2fzn calls;
 * **output_dir**: Set a default output directory for generated files;
 * **force_flatten**: Overrides the force_flatten flag of all minizinc calls;
 * **dzn_width**: The horizontal character limit for dzn files;
   This property is used to wrap long dzn statements when writing dzn files.
   This property is also used in the ``pymzn.minizinc`` function as a limit to
   decide whether to write the inline data into a file.

One can also set custom properties to be used for custom solvers.


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

_config = {}


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
    _config[key] = value

