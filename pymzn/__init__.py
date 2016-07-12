"""
Wrapper module for the MiniZinc tool pipeline.
"""
from pymzn.mzn import *
from pymzn.dzn import *

__version__ = '0.9.9'
__all__ = ['mzn', 'dzn', 'debug']

# TODO: make a better documentation
# TODO: upload documentation online (github)
# TODO: update python2 branch
# TODO: config solver function and default arguments to solver
# TODO: mzn2doc
# TODO: make it work on windows

import logging
debug_handler = None
pymzn_log = logging.getLogger(__name__)
pymzn_log.addHandler(logging.NullHandler())


def debug(verb=True):
    global pymzn_log
    global debug_handler
    if verb and debug_handler is None:
        debug_handler = logging.StreamHandler()
        pymzn_log.addHandler(debug_handler)
        pymzn_log.setLevel(logging.DEBUG)
    elif not verb and debug_handler is not None:
        pymzn_log.removeHandler(debug_handler)
        debug_handler = None
        pymzn_log.setLevel(logging.WARNING)
