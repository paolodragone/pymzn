"""Wrapper module for the MiniZinc tool pipeline."""
import logging

from .config import mzn2fzn_cmd, solns2out_cmd, gecode_cmd, optimatsat_cmd
from .mzn import (minizinc, mzn2fzn, solns2out, gecode, solve, MiniZincModel,
                  MiniZincUnknownError, MiniZincUnsatisfiableError,
                  MiniZincUnboundedError)
from .dzn import dzn, dzn_value, rebase_array, parse_dzn

__version__ = '0.9.9'

# TODO: update the README
# TODO: make a better documentation
# TODO: upload documentation online (github)
# TODO: update python2 branch
# TODO: config solver function and default arguments to solver

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
