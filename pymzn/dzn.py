# -*- coding: utf-8 -*-
"""Utilities to convert Python objects into dzn format and back."""

import logging
import re
from numbers import Number, Integral
from collections import Sized, Iterable, Set, Mapping


# FIXME: Output format of the old parsing function compliant to the new one

""" PYTHON TO DZN """


def _is_int(obj):
    return isinstance(obj, Integral)


def _is_value(obj):
    return isinstance(obj, (bool, str, Number))


def _is_set(obj):
    return isinstance(obj, Set) and all(map(_is_value, obj))


def _is_elem(obj):
    return _is_value(obj) or _is_set(obj)


def _is_list(obj):
    return (isinstance(obj, Sized) and isinstance(obj, Iterable) and
            not isinstance(obj, (Set, Mapping)))


def _is_dict(obj):
    return isinstance(obj, Mapping)


def _is_array_type(obj):
    return _is_list(obj) or _is_dict(obj)


def _list_index_set(obj):
    return 1, len(obj)


def _dict_index_set(obj):
    min_val = min(obj.keys())
    max_val = max(obj.keys())
    return min_val, max_val


def _is_contiguous(obj):
    if all(map(_is_int, obj)):
        min_val, max_val = min(obj), max(obj)
        return all([v in obj for v in range(min_val, max_val + 1)])
    return False


def _index_set(obj):
    if _is_list(obj):
        if len(obj) == 0:
            return ()
        if all(map(_is_elem, obj)):
            return _list_index_set(obj),
        elif all(map(_is_array_type, obj)):
            idx_sets = list(map(_index_set, obj))
            # all children index-sets must be identical
            if idx_sets[1:] == idx_sets[:-1]:
                return (_list_index_set(obj),) + idx_sets[0]
    elif _is_dict(obj):
        if len(obj) == 0:
            return ()
        if _is_contiguous(obj.keys()):
            if all(map(_is_elem, obj.values())):
                return _dict_index_set(obj),
            elif all(map(_is_array_type, obj.values())):
                idx_sets = list(map(_index_set, obj.values()))
                # all children index-sets must be identical
                if idx_sets[1:] == idx_sets[:-1]:
                    return (_dict_index_set(obj),) + idx_sets[0]
    raise ValueError('The input object is not a proper array: '
                     '{}'.format(repr(obj)), obj)


def _flatten_array(arr, lvl):
    if lvl == 1:
        return arr
    flat_arr = []

    if _is_dict(arr):
        arr_it = arr.values()
    else:
        arr_it = arr

    for sub_arr in arr_it:
        for item in _flatten_array(sub_arr, lvl - 1):
            flat_arr.append(item)
    return flat_arr


def _dzn_val(val):
    if isinstance(val, bool):
        return 'true' if val else 'false'
    return str(val)


def _dzn_var(name, val):
    return '{} = {};'.format(name, val)


def _dzn_set(vals):
    if _is_contiguous(vals):
        min_val, max_val = min(vals), max(vals)
        return '{}..{}'.format(min_val, max_val)  # contiguous set
    return '{{ {} }}'.format(', '.join(map(_dzn_val, vals)))


def _dzn_array_nd(arr):
    idx_set = _index_set(arr)
    dim = max([len(idx_set), 1])
    if dim > 6:  # max 6-dimensional array in dzn language
        raise ValueError('The input array has {} dimensions. Minizinc supports'
                         ' arrays of up to 6 dimensions.'.format(dim), arr)

    if _is_dict(arr):
        arr_it = arr.values()
    else:
        arr_it = arr
    flat_arr = _flatten_array(arr_it, dim)

    dzn_arr = 'array{}d({}, {})'
    if len(idx_set) > 0:
        idx_set_str = ', '.join(['{}..{}'.format(*s) for s in idx_set])
    else:
        idx_set_str = '{}'
    arr_str = '[{}]'.format(', '.join(map(_dzn_val, flat_arr)))
    return dzn_arr.format(dim, idx_set_str, arr_str)


def dzn_value(val):
    """
    Serializes a value (bool, int, float, set, array) into its dzn
    representation.

    :param val: The value to serialize
    :return: The serialized dzn representation of the value
    """
    if _is_value(val):
        return _dzn_val(val)
    elif _is_set(val):
        return _dzn_set(val)
    elif _is_array_type(val):
        return _dzn_array_nd(val)
    raise TypeError('Unsupported parsing for value: {}'.format(repr(val)), val)


def dzn(objs, fout=None):
    """
    Serializes the objects in input and produces a list of strings encoding
    them into the dzn format. Optionally, the produced dzn is written in a
    given file.

    Supported types of objects include: str, int, float, set, list or dict.
    List and dict are serialized into dzn (multi-dimensional) arrays. The
    key-set of a dict is used as index-set of dzn arrays. The index-set of a
    list is implicitly set to 1..len(list).

    :param dict objs: A dictionary containing key-value pairs where keys are
                      the names of the variables
    :param str fout: Path to the output file, if None no output file is written
    :return: List of strings containing the dzn encoded objects
    :rtype: list
    """

    vals = [_dzn_var(key, dzn_value(val)) for key, val in objs.items()]

    if fout:
        with open(fout, 'w') as f:
            for val in vals:
                f.write('{}\n'.format(val))
    return vals


""" DZN TO PYTHON """

# For now support only numerical values and numeric arrays and sets

# boolean pattern
_bool_p = re.compile('^(?:true|false)$')

# integer pattern
_int_p = re.compile('^[+\-]?\d+$')

# float pattern
_float_p = re.compile('^[+\-]?\d*\.\d+(?:[eE][+\-]?\d+)?$')

# continuous integer set pattern
_cont_int_set_p = re.compile('^([+\-]?\d+)\.\.([+\-]?\d+)$')

# integer set pattern
_int_set_p = re.compile('^(\{(?P<vals>[\d ,+\-]*)\})$')

# matches any of the previous
_val_p = re.compile(('(?:true|false|\{(?:[\d ,+\-]+)\}'
                     '|(?:[+\-]?\d+)\.\.(?:[+\-]?\d+)'
                     '|[+\-]?\d*\.\d+(?:[eE][+\-]?\d+)?'
                     '|[+\-]?\d+)'))

# multi-dimensional array pattern
_array_p = re.compile(('^(?:array(?P<dim>\d)d\s*'
                       '\((?P<indices>(?:\s*[\d\.+\-]+(\s*,\s*)?)+)\s*,\s*)?'
                       '\[(?P<vals>[\w \.,+\-\\\/\*^|\(\)\{\}]+)\]\)?$'))

# variable pattern
_var_p = re.compile(('^\s*(?P<var>[\w]+)\s*=\s*(?P<val>[\w \.,+\-\\\/\*^|\('
                     '\)\[\]\{\}]+);?$'))


def dict2list(d):
    """
    Transform an indexed dictionary (such as those returned by the parse_dzn
    function when parsing arrays) into an multi-dimensional array.

    :param dict d: The indexed dictionary to convert
    :return: A multi-dimensional array
    :rtype: list
    """
    arr = []
    min_val, max_val = _dict_index_set(d)
    idx_set = range(min_val, max_val + 1)
    for idx in idx_set:
        v = d[idx]
        if _is_dict(v):
            v = dict2list(v)
        arr.append(v)
    return arr


def _parse_array(indices, vals):
    # Recursive parsing of multi-dimensional arrays returned by the solns2out
    # utility of the type: array2d(2..4, 1..3, [1, 2, 3, 4, 5, 6, 7, 8, 9])
    idx_set = indices[0]
    if len(indices) == 1:
        arr = {i: _parse_val(vals.pop(0)) for i in idx_set}
    else:
        arr = {i: _parse_array(indices[1:], vals) for i in idx_set}
    return arr


def _parse_indices(st):
    # Parse indices inside multi-dimensional arrays
    ss = st.strip().split(',')
    indices = []
    for s in ss:
        s = s.strip()
        cont_int_set_m = _cont_int_set_p.match(s)
        if cont_int_set_m:
            v1 = int(cont_int_set_m.group(1))
            v2 = int(cont_int_set_m.group(2))
            indices.append(range(v1, v2 + 1))
        else:
            raise ValueError('Index \'{}\' is not well formatted.'.format(s))
    return indices


def _parse_set(vals):
    # Parse sets of integers of the type: {41, 2, 53, 12, 8}
    p_s = set()
    for val in vals:
        p_val = val.strip()
        if _int_p.match(p_val):
            p_val = int(p_val)
            p_s.add(p_val)
        else:
            raise ValueError('A value of the input set is not an integer: '
                             '{}'.format(repr(p_val)), p_val)
    return p_s


def _parse_val(val):
    # boolean value
    if _bool_p.match(val):
        return {'true': True, 'false': False}[val]

    # integer value
    if _int_p.match(val):
        return int(val)

    # float value
    if _float_p.match(val):
        return float(val)

    # continuous integer set
    cont_int_set_m = _cont_int_set_p.match(val)
    if cont_int_set_m:
        v1 = int(cont_int_set_m.group(1))
        v2 = int(cont_int_set_m.group(2))
        return set(range(v1, v2 + 1))

    # integer set
    set_m = _int_set_p.match(val)
    if set_m:
        vals = set_m.group('vals')
        if vals:
            return _parse_set(vals.split(','))
        return set()
    return None


def parse_dzn(lines):
    """
    Parse the one solution from the output stream of the solns2out utility.

    :param [str] lines: The stream of lines from a given solution
    :return: A dictionary containing the variable assignments parsed from
             the input stream
    :rtype: dict
    """
    log = logging.getLogger(__name__)
    parsed_vars = {}
    for l in lines:
        l = l.strip()
        log.debug('Parsing line: %s', l)
        var_m = _var_p.match(l)
        if var_m:
            var = var_m.group('var')
            val = var_m.group('val')
            p_val = _parse_val(val)
            if p_val is not None:
                parsed_vars[var] = p_val
                log.debug('Parsed value: %s', p_val)
                continue

            log.debug('Parsing array: %s', val)
            array_m = _array_p.match(val)
            if array_m:
                vals = array_m.group('vals')
                vals = _val_p.findall(vals)
                dim = array_m.group('dim')
                if dim:  # explicit dimensions
                    dim = int(dim)
                    indices = array_m.group('indices')
                    log.debug('Parsing indices: %s', indices)
                    indices = _parse_indices(indices)
                    assert len(indices) == dim
                    log.debug('Parsing values: %s', vals)
                    p_val = _parse_array(indices, vals)
                else:  # assuming 1d array based on 0
                    log.debug('Parsing values: %s', vals)
                    p_val = _parse_array([range(len(vals))], vals)
                parsed_vars[var] = p_val
                log.debug('Parsed array: %s', p_val)
                continue
        raise ValueError('Unsupported parsing for line:\n{}'.format(l), l)
    return parsed_vars
