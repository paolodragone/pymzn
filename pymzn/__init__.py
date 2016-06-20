# -*- coding: utf-8 -*-
"""Wrapper module for the MiniZinc tool pipeline."""
__version__ = '0.9.6'

import pymzn.binary
from .mzn import fzn_gecode, minizinc, mzn2fzn, solns2out
from .dzn import dzn, parse_dzn, dict2array, MiniZincParsingError
