# -*- coding: utf-8 -*-
"""PyMzn is a Python library that wraps and enhances the MiniZinc tools for
modelling and solving constraint programs. It is built on top of the MiniZinc
toolkit and provides a number of off-the-shelf functions to readily solve
problems encoded in MiniZinc and parse the solutions into Python objects."""

from .log import *
from .config import config
from .dzn import *
from .mzn import *

__all__ = ['config'] + log.__all__ + dzn.__all__ + mzn.__all__


__version__ = '0.17.1'


def main():
    import ast
    import argparse
    from textwrap import dedent

    def _minizinc(**_args):
        print(minizinc(
        _args['mzn'], *_args['dzn_files'],
        **{k: v for k, v in _args.items() if k not in ['mzn', 'dzn_files']}
    ))

    def _config(key, value=None, delete=False, **__):
        if delete:
            del config[key]
            config.dump()
        elif value is None:
            print('{} : {}'.format(key, config.get(key)))
        else:
            config[key] = value
            config.dump()

    desc = dedent('''\
        PyMzn is a Python library that wraps and enhances the MiniZinc tools for
        modelling and solving constraint programs. It is built on top of the
        MiniZinc toolkit and provides a number of off-the-shelf functions to
        readily solve problems encoded in MiniZinc and parse the solutions into
        Python objects.
    ''')

    fmt = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description=desc, formatter_class=fmt)
    parser.add_argument(
        '--version', action='version',
        version='PyMzn version: {}'.format(__version__)
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='display informative messages on standard output'
    )

    # minizinc
    parser.add_argument(
        'mzn', help='the mzn file to solve'
    )
    parser.add_argument(
        'dzn_files', nargs='*', help='additional dzn files'
    )
    parser.add_argument(
        '--data', type=ast.literal_eval, help='additional inline data'
    )
    parser.add_argument(
        '-a', '--all-solutions', action='store_true',
        help='wheter to return all solutions (if supported by the solver)'
    )
    parser.add_argument(
        '-S', '--solver', help='name of the solver'
    )
    parser.add_argument(
        '-s', '--solver-args', type=ast.literal_eval, default={},
        help='arguments to pass to the solver'
    )
    parser.add_argument(
        '-k', '--keep', action='store_true',
        help='whether to keep generated files'
    )
    parser.add_argument(
        '-I', '--include', dest='path', action='append',
        help='directory the standard library'
    )
    parser.set_defaults(func=_minizinc)

    # config
    subparsers = parser.add_subparsers()
    config_parser = subparsers.add_parser(
        'config', help='config pymzn variables'
    )
    config_parser.add_argument(
        'key', help='the property to get/set'
    )
    config_parser.add_argument(
        '-d', '--delete', action='store_true', help='delete a key'
    )
    config_parser.add_argument(
        'value', nargs='?', help='the value(s) to set'
    )
    config_parser.set_defaults(func=_config)

    args = parser.parse_args()

    debug(args.verbose)
    args.func(**{**vars(args), **args.solver_args})


if __name__ == '__main__':
    main()

