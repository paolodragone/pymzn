# -*- coding: utf-8 -*-
"""\
PyMzn is a Python library that wraps and enhances the MiniZinc tools for
constraint programming. PyMzn is built on top of the minizinc toolkit and
provides a number of off-the-shelf functions to readily solve problems encoded
with the MiniZinc language and return solutions as Python dictionaries.
"""

from .log import *
from .config import config
from .dzn import *
from .mzn import *

__all__ = ['config'] + log.__all__ + dzn.__all__ + mzn.__all__


__version__ = '0.18.3'


def main():
    import sys
    import ast
    import argparse

    def _minizinc(
        no_declare_enums=False, solver=None, output_file=None, solver_log=False,
        **_args
    ):
        if no_declare_enums:
            _args['declare_enums'] = False

        if 'compile' in _args and _args['compile']:
            other_args = {
                k: v for k, v in _args.items() if k not in ['mzn', 'dzn_files']
            }
            mzn2fzn(_args['mzn'], *_args['dzn_files'], **other_args)
            return

        if solver:
            from .mzn import solvers
            _args['solver'] = getattr(solvers, solver)

        solns = minizinc(
            _args['mzn'], *_args['dzn_files'], keep_solutions=False,
            **{k: v for k, v in _args.items() if k not in ['mzn', 'dzn_files']}
        )

        if output_file:
            out = open(output_file, 'w+')
        else:
            out = sys.stdout

        if 'output_mode' in _args and _args['output_mode'] == 'raw':
            print(solns, file=out)
        else:
            solns.print(output_file=out, log=solver_log)
        out.close()

    def _config(key=None, value=None, delete=False, **__):
        if not key:
            print('\n'.join(list(config.keys())))
        elif delete:
            del config[key]
            config.dump()
        elif value is None:
            print('{} : "{}"'.format(key, config.get(key)))
        else:
            config[key] = value
            config.dump()

    desc = sys.modules[__name__].__doc__
    fmt = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description=desc, formatter_class=fmt)
    parser.add_argument(
        '--version', action='version',
        version=(
            'PyMzn, version {} | Copyright (c) 2016 Paolo Dragone'
        ).format(__version__)
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='display informative messages'
    )

    subparsers = parser.add_subparsers()

    # minizinc
    minizinc_parser = subparsers.add_parser(
        'minizinc', help='execute minizinc'
    )
    minizinc_parser.add_argument(
        'mzn', help='the mzn file to solve'
    )

    flattener_options = minizinc_parser.add_argument_group('Flattener options')
    flattener_options.add_argument(
        'dzn_files', nargs='*', help='additional dzn files'
    )
    flattener_options.add_argument(
        '--data', type=ast.literal_eval, help='additional inline data'
    )
    flattener_options.add_argument(
        '--args', type=ast.literal_eval,
        help='additional arguments for the template engine'
    )
    flattener_options.add_argument(
        '--output-vars', type=ast.literal_eval,
        help='list of variables to output'
    )
    flattener_options.add_argument(
        '-I', '--include', dest='path', action='append',
        help='additional search directories'
    )
    flattener_options.add_argument(
        '--stdlib-dir', help='path to MiniZinc standard library directory'
    )
    flattener_options.add_argument(
        '-G', '--globals-dir', help='name of directory including globals'
    )
    flattener_options.add_argument(
        '-c', '--compile', action='store_true',
        help='compile only'
    )
    flattener_options.add_argument(
        '-k', '--keep', action='store_true',
        help='keep generated files'
    )
    flattener_options.add_argument(
        '--two-pass', type=int, help='equivalent to MiniZinc -O<n> option'
    )
    flattener_options.add_argument(
        '--pre-passes', type=int,
        help='equivalent to MiniZinc --pre-passes option'
    )

    solver_options = minizinc_parser.add_argument_group('Solver options')
    solver_options.add_argument(
        '-S', '--solver', help='name of the solver'
    )
    solver_options.add_argument(
        '-a', '--all-solutions', action='store_true',
        help='return all solutions (if supported by the solver)'
    )
    solver_options.add_argument(
        '-n', '--num-solutions', type=int, help='number of solutions to return'
    )
    solver_options.add_argument(
        '-t', '--timeout', type=int,
        help='time limit for flattening and solving (in seconds)'
    )
    solver_options.add_argument(
        '-p', '--parallel', type=int,
        help='the number of threads the solver should use'
    )
    solver_options.add_argument(
        '-f', '--free-search', action='store_true',
        help='instruct the solver to run a free search'
    )
    solver_options.add_argument(
        '-r', '--seed', type=int, help='the random seed for the user'
    )
    solver_options.add_argument(
        '--solver-args', type=ast.literal_eval, default={},
        help='additional arguments to pass to the solver'
    )

    output_options = minizinc_parser.add_argument_group('Output options')
    output_options.add_argument(
        '-o', '--output-file',
        help='path to the output file (default print on standard output)'
    )
    output_options.add_argument(
        '-l', '--solver-log', action='store_true', help='print solver\'s log'
    )
    output_options.add_argument(
        '--output-mode', choices=['dict', 'item', 'dzn', 'json', 'raw'],
        default='dict', help='the output format'
    )
    output_options.add_argument(
        '--output-objective', action='store_true',
        help='print the value of the objective'
    )
    output_options.add_argument(
        '--non-unique', action='store_true',
        help='allow for non unique solutions'
    )
    output_options.add_argument(
        '--allow-multiple-assignments', action='store_true',
        help='equivalent to MiniZinc allow-multiple-assigments option'
    )
    output_options.add_argument(
        '--no-declare-enums', action='store_true',
        help='do not declare enums when serializing enum values'
    )

    minizinc_parser.set_defaults(func=_minizinc)


    # config
    config_parser = subparsers.add_parser(
        'config', help='config pymzn variables'
    )
    config_parser.add_argument(
        'key', nargs='?', help='the property to get/set'
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

    args = vars(args)
    if 'solver_args' in args:
        args.update(args['solver_args'])

    args['func'](**args)


if __name__ == '__main__':
    main()

