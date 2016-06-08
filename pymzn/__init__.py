# -*- coding: utf-8 -*-
"""Wrapper module for the MiniZinc tool pipeline."""
__version__ = '0.9.3'

from .mzn import fzn_gecode, minizinc, mzn2fzn, solns2out, MiniZincError, run
from .dzn import dzn, parse_dzn, dict2array, MiniZincParsingError
