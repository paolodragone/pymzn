# -*- coding: utf-8 -*-
"""PyMzn is a Python library that wraps and enhances the MiniZinc tools for CSP
modelling and solving. It is built on top of the libminizinc library (version
2.0) and provides a number of off-the-shelf functions to readily solve problems
encoded in MiniZinc and evaluate the solutions into Python objects.
"""

import ast
import logging

from . import config
from . import _utils
from . import bin
from . import _dzn
from ._dzn import *
from . import _mzn
from ._mzn import *

__version__ = '0.10.8'
__all__ = ['debug', 'config', 'bin']
__all__.extend(_dzn.__all__)
__all__.extend(_mzn.__all__)

# TODO: update python2 branch
# TODO: config solver function and default arguments to solver
# TODO: make it work on windows
# TODO: check the ctrl+C thing which seems to not work anymore

_debug_handler = None
_pymzn_logger = logging.getLogger(__name__)
_pymzn_logger.addHandler(logging.NullHandler())

def debug(dbg=True):
    global _debug_handler
    if dbg and _debug_handler is None:
        _debug_handler = logging.StreamHandler()
        _pymzn_logger.addHandler(_debug_handler)
        _pymzn_logger.setLevel(logging.DEBUG)
    elif not dbg and _debug_handler is not None:
        _pymzn_logger.removeHandler(_debug_handler)
        _debug_handler = None
        _pymzn_logger.setLevel(logging.WARNING)


def main():
    import argparse
    from textwrap import dedent

    def _minizinc(**_args):
        print(minizinc(**_args))

    def _config(key, value=None):
        if value is None:
            print('{} : {}'.format(key, config.get(key)))
        else:
            config.set(key, value)
            config.dump()

    #TODO: finish description
    desc = dedent('''PyMzn is a wrapper for the MiniZinc tool pipeline.
    ''')

    fmt = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description=desc, formatter_class=fmt)
    parser.add_argument('--version', action='version',
                        version='PyMzn version: {}'.format(__version__))
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='display informative messages on standard output')

    subparsers = parser.add_subparsers()
    mzn_parser = subparsers.add_parser('minizinc',
                                      help='solve a minizinc problem')
    mzn_parser.add_argument('mzn',
                            help='the mzn file to solve')
    mzn_parser.add_argument('dzn_files', nargs='*',
                            help='additional dzn files')
    mzn_parser.add_argument('--data', type=ast.literal_eval,
                            help='additional inline data')
    mzn_parser.add_argument('-S', '--solver',
                            help='name of the solver')
    mzn_parser.add_argument('-s', '--solver-args', type=ast.literal_eval,
                            default={},
                            help='arguments to pass to the solver')
    mzn_parser.add_argument('-k', '--keep', action='store_true',
                            help='whether to keep generated files')
    mzn_parser.add_argument('-o', '--output-base',
                            help='base name for generated files if keeped')
    mzn_parser.add_argument('-G', '--globals-dir',
                            help=('directory of global files in the standard '
                                  'library'))
    mzn_parser.add_argument('-I', '--include', dest='path', action='append',
                            help='directory the standard library')
    mzn_parser.add_argument('--stdlib-dir',
                            help='directory the standard library')
    mzn_parser.add_argument('--no-eval', dest='eval_output',
                            action='store_false',
                            help=('return the content of the original output '
                                  'statement'))
    mzn_parser.set_defaults(func=_minizinc)

    config_parser = subparsers.add_parser('config',
                                         help='config pymzn variables')
    config_parser.add_argument('key',
                               help='the property to get/set')
    config_parser.add_argument('value', nargs='?',
                               help='the value(s) to set')
    config_parser.set_defaults(func=_config)

    args = parser.parse_args()

    debug(args.verbose)
    args.func(**vars(args))


if __name__ == '__main__':
    main()

