"""
Wrapper module for the MiniZinc tool pipeline.
"""

__version__ = '0.10.1'

import logging

from . import _mzn
from . import _dzn
from ._mzn import *
from ._dzn import *
from . import bin
from . import config

__all__ = ['bin', 'config', 'debug']
__all__.extend(_mzn.__all__)
__all__.extend(_dzn.__all__)


# TODO: update python2 branch
# TODO: config solver function and default arguments to solver
# TODO: mzn2doc
# TODO: check the import of other files in minizinc
# TODO: make it work on windows
# TODO: make a main function and runnable from command line


debug_handler = None
pymzn_log = logging.getLogger(__name__)
pymzn_log.addHandler(logging.NullHandler())


def debug(dbg=True):
    global debug_handler
    if dbg and debug_handler is None:
        debug_handler = logging.StreamHandler()
        pymzn_log.addHandler(debug_handler)
        pymzn_log.setLevel(logging.DEBUG)
    elif not dbg and debug_handler is not None:
        pymzn_log.removeHandler(debug_handler)
        debug_handler = None
        pymzn_log.setLevel(logging.WARNING)
