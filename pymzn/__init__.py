# -*- coding: utf-8 -*-
"""Wrapper module for the MiniZinc tool pipeline."""
__version__ = '0.9.7'

from .mzn import minizinc, mzn2fzn, solns2out, fzn_gecode, \
    MiniZincUnknownError, MiniZincUnsatisfiableError
from .dzn import dzn, parse_dzn, dict2list
