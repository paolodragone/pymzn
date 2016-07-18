"""
PyMzn is a Python library that wraps and enhances the MiniZinc tools for CSP
modelling and solving. It is built on top of the libminizinc library
(version 2.0) and provides a number of off-the-shelf functions to readily
solve problems encoded in MiniZinc and parse the solutions into Python objects.
"""
import ast
import logging

from . import config
from . import bin
from . import _dzn
from ._dzn import *
from . import _mzn
from ._mzn import *

__version__ = '0.10.2'
__all__ = ['debug', 'config', 'bin']
__all__.extend(_dzn.__all__)
__all__.extend(_mzn.__all__)

# TODO: update python2 branch
# TODO: config solver function and default arguments to solver
# TODO: mzn2doc
# TODO: check the import of other files in minizinc
# TODO: make it work on windows


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


def main():
    import argparse

    desc = 'PyMzn is a wrapper for the MiniZinc tool pipeline.'
    p = argparse.ArgumentParser(description=desc)
    p.add_argument('-d', '--debug', action='store_true',
                   help='display debug messages on standard output')
    p.add_argument('mzn', help='the mzn file to solve')
    p.add_argument('dzn_files', nargs='*', help='additional dzn files')
    p.add_argument('-D', '--data', type=ast.literal_eval,
                   help='additional inline data')
    p.add_argument('-k', '--keep', action='store_true',
                   help='whether to keep generated files')
    p.add_argument('-o', '--output-base',
                   help='base name for generated files')
    p.add_argument('-G', '--mzn-globals-dir',
                   help='directory of global files in the standard library')
    p.add_argument('-f', '--fzn-fn',
                   help='name of proxy function for the solver')
    p.add_argument('--fzn-args', type=ast.literal_eval, default={},
                   help='arguments to pass to the solver')
    args = p.parse_args()

    if args.debug:
        debug()

    other_args = {**{'data': args.data, 'keep': args.keep,
                     'output_base': args.output_base,
                     'mzn_globals_dir': args.mzn_globals_dir,
                     'fzn_fn': args.fzn_fn}, **args.fzn_args}

    print(minizinc(args.mzn, *args.dzn_files, raw_output=True, **other_args))
