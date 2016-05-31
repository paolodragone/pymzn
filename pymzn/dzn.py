# -*- coding: utf-8 -*-
"""Utilities to convert Python objects into dzn files."""


def dzn_var(name, val):
    return '{} = {};\n'.format(name, val)


def dzn_set(vals, sep=', '):
    return '{{ {} }}'.format(sep.join(map(str, vals)))


def dzn_array(array, sep=', '):
    return '[{}]'.format(sep.join(map(str, array)))


def dzn_matrix(matrix):
    rows = '\n'.join(['|' + ', '.join(map(str, row)) for row in matrix])
    return '[{}|]'.format(rows)


def dzn(objs, fout=None):
    """
    Parse the objects in input and produces a list of strings encoding them
    into the dzn format. Optionally, the produced dzn is written in a given
    file.

    Supported types of objects include: str, int, float, set, list or list of
    list of the previous.

    :param dict objs: A dictionary containing key-value pairs where keys are
                      the names of the variables
    :param str fout: Path to the output file, if None no output file is written
    :return: List of strings containing the dzn encoded objects
    :rtype: list
    """

    def is_value(v):
        return isinstance(v, (str, int, float))

    def is_set(v):
        return isinstance(v, set)

    def is_array(v):
        return all([is_value(e) or is_set(e) for e in v])

    def is_matrix(v):
        if isinstance(v[0], list):
            l = len(v[0])
            return all([isinstance(e, list) and len(e) == l and is_array(e)
                        for e in v])
        return False

    vals = []
    for key, val in objs.items():
        if is_value(val):
            vals.append(dzn_var(key, val))
        elif is_set(val):
            s = dzn_set(val)
            vals.append(dzn_var(key, s))
        elif isinstance(val, list):
            if is_array(val):
                a = dzn_array(val)
                vals.append(dzn_var(key, a))
            elif is_matrix(val):
                m = dzn_matrix(val)
                vals.append(dzn_var(key, m))
            else:
                msg = 'The value for key \'{}\' is a list but it is not an ' \
                      'array nor a matrix: {}'.format(key, val)
                raise RuntimeError(msg)
        else:
            msg = 'Unsupported parsing for the value of ' \
                  'key \'{}\': {}'.format(key, val)
            raise RuntimeError(msg)

    if fout:
        with open(fout, 'w') as f:
            for val in vals:
                f.write(val)

    return vals
