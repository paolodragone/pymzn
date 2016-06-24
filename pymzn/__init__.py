# -*- coding: utf-8 -*-
"""Wrapper module for the MiniZinc tool pipeline."""
import logging

from .mzn import minizinc, mzn2fzn, solns2out, fzn_gecode, \
    MiniZincUnknownError, MiniZincUnsatisfiableError
from .dzn import dzn, parse_dzn, dict2list

__version__ = '0.9.7'

debug_handler = None


def turn_on_debug():
    log = logging.getLogger(__name__)
    global debug_handler
    if debug_handler is None:
        debug_handler = logging.StreamHandler()
        log.addHandler(debug_handler)
        log.setLevel(logging.DEBUG)


def turn_off_debug():
    log = logging.getLogger(__name__)
    global debug_handler
    if debug_handler is not None:
        log.removeHandler(debug_handler)
        debug_handler = None
        log.setLevel(logging.WARNING)
