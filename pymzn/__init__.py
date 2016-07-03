# -*- coding: utf-8 -*-
"""Wrapper module for the MiniZinc tool pipeline."""

import logging

from .mzn import minizinc, mzn2fzn, solns2out, fzn_gecode, MiniZincModel, \
    MiniZincUnknownError, MiniZincUnsatisfiableError, MiniZincUnboundedError
from .dzn import dzn, dzn_value, dict2list, parse_dzn

__version__ = '0.9.8'

debug_handler = None
pymzn_log = logging.getLogger(__name__)
pymzn_log.addHandler(logging.NullHandler())

# TODO: update the README
# TODO: update python2 branch


def verbose(verb):
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
