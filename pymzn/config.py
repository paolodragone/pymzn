# -*- coding: utf-8 -*-
"""\
PyMzn can be configured with custom executable paths and other variables.
Configuration is done via the ``pymzn.config`` object. For instance:

.. code-block:: python3

    import pymzn
    pymzn.config.set('minizinc', 'path/to/minizinc')

The configurable properties used by PyMzn are the following:

 * **minizinc**: Path to the minizinc executable;
 * **solver**: Solver instance to use when calling pymzn.minizinc;
 * **solver_args**: Arguments to pass to the solver when calling pymzn.minizinc;
 * **args**: Additional arguments to pass to the template engine;
 * **include**: List of search paths to include in all minizinc calls;
 * **keep**: Overrides the keep flag of all minizinc calls;
 * **dzn_width**: The horizontal character limit for dzn files;
   This property is used to wrap long dzn statements when writing dzn files.
   This property is also used in the minizinc function as a limit to decide
   whether to write the inline data into a file.

One can also set custom properties to be used for custom solvers.

The configuration of PyMzn can be made permanent by using the ``dump`` function
of the ``config`` object:

.. code-block:: python3

    pymzn.config.dump()

This operation, as well as loading the saved configuration file, requires the
``appdirs`` and ``pyyaml`` libraries to be installed on your system.


Debug
-----

PyMzn can also be set to print debugging messages on standard output via:

.. code-block:: python3

    pymzn.debug()

This function is meant to be used in interactive sessions or in
applications that do not configure the ``logging`` library. If you configure the
``logging`` library in your application, then PyMzn will print logging messages
as well. To disable debugging messages you can then call:

.. code-block:: python3

    pymzn.debug(False)

"""

import os


class Config(dict):

    _defaults = {
        'minizinc': 'minizinc',
        'dzn_width': 70
    }

    def __init__(self, **kwargs):
        super().__init__(**{**Config._defaults, **kwargs})

        try:
            import yaml
            cfg_file = self._cfg_file()
            if cfg_file and os.path.isfile(cfg_file):
                with open(cfg_file) as f:
                    _config = yaml.load(f)
                self.update(_config)
        except ImportError:
            pass

    def __setattr__(self, key, value):
        self[key] = value

    def __dir__(self):
        return self.keys()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setstate__(self, state):
        pass

    def _cfg_file(self):
        try:
            import appdirs
            return os.path.join(appdirs.user_config_dir(__name__), 'config.yml')
        except ImportError:
            return None

    def dump(self):
        """Writes the changes to the configuration file."""
        try:
            import yaml
            cfg_file = self._cfg_file()
            cfg_dir, __ = os.path.split(cfg_file)
            os.makedirs(cfg_dir, exist_ok=True)
            with open(cfg_file, 'w') as f:
                yaml.dump(self, f)
        except ImportError as err:
            raise RuntimeError(
                'Cannot dump the configuration settings to file. You need to '
                'install the necessary dependencies (pyyaml, appdirs).'
            ) from err


config = Config()

