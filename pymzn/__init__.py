# -*- coding: utf-8 -*-
u"""PyMzn is a Python library that wraps and enhances the MiniZinc tools for CSP
modelling and solving. It is built on top of the MiniZinc toolkit and provides a
number of off-the-shelf functions to readily solve problems encoded in MiniZinc
and parse the solutions into Python objects.
"""

from __future__ import absolute_import
import ast
import logging

from . import config
from . import utils
from . import dzn
from .dzn import *
from . import mzn
from .mzn import *

__version__ = u'0.14.0'
__all__ = [u'debug', u'config']
__all__.extend(dzn.__all__)
__all__.extend(mzn.__all__)

# TODO: update python2 branch
# TODO: make it work on windows

_debug_handler = None
_pymzn_logger = logging.getLogger(__name__)
_pymzn_logger.addHandler(logging.NullHandler())

def debug(dbg=True):
    u"""Enables or disables debugging messages on the standard output."""
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
        print minizinc(**_args)

    def _config(key, value=None, **__):
        if value is None:
            print u'{} : {}'.format(key, config.get(key))
        else:
            config.set(key, value)
            config.dump()

    desc = dedent(u'''\
        PyMzn is a Python library that wraps and enhances the MiniZinc tools for
        CSP modelling and solving. It is built on top of the MiniZinc toolkit
        and provides a number of off-the-shelf functions to readily solve
        problems encoded in MiniZinc and parse the solutions into Python
        objects.
    ''')

    fmt = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description=desc, formatter_class=fmt)
    parser.add_argument(u'--version', action=u'version',
                        version=u'PyMzn version: {}'.format(__version__))
    parser.add_argument(u'-v', u'--verbose', action=u'store_true',
                        help=u'display informative messages on standard output')

    subparsers = parser.add_subparsers()
    mzn_parser = subparsers.add_parser(u'minizinc',
                                      help=u'solve a minizinc problem')
    mzn_parser.add_argument(u'mzn',
                            help=u'the mzn file to solve')
    mzn_parser.add_argument(u'dzn_files', nargs=u'*',
                            help=u'additional dzn files')
    mzn_parser.add_argument(u'--data', type=ast.literal_eval,
                            help=u'additional inline data')
    mzn_parser.add_argument(u'-a', u'--all-solutions', action=u'store_true',
                            help=(u'wheter to return all solutions '
                                  u'(if supported by the solver)'))
    mzn_parser.add_argument(u'-S', u'--solver',
                            help=u'name of the solver')
    mzn_parser.add_argument(u'-s', u'--solver-args', type=ast.literal_eval,
                            default={},
                            help=u'arguments to pass to the solver')
    mzn_parser.add_argument(u'-k', u'--keep', action=u'store_true',
                            help=u'whether to keep generated files')
    mzn_parser.add_argument(u'-I', u'--include', dest=u'path', action=u'append',
                            help=u'directory the standard library')
    mzn_parser.set_defaults(func=_minizinc)

    config_parser = subparsers.add_parser(u'config',
                                         help=u'config pymzn variables')
    config_parser.add_argument(u'key',
                               help=u'the property to get/set')
    config_parser.add_argument(u'value', nargs=u'?',
                               help=u'the value(s) to set')
    config_parser.set_defaults(func=_config)

    args = parser.parse_args()

    debug(args.verbose)
    args.func(**set([**vars(args), **args.solver_args]))


if __name__ == u'__main__':
    main()

