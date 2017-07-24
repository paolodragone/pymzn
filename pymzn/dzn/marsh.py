# -*- coding: utf-8 -*-

import logging
import pymzn.config as config

from textwrap import TextWrapper
from numbers import Integral, Real, Number
from collections.abc import Set, Sized, Iterable, Mapping

_wrapper = None

def _get_wrapper():
    global _wrapper
    if not _wrapper:
        _wrapper = TextWrapper(width=config.get('dzn_width', 70),
                               subsequent_indent=' '*4, break_long_words=False,
                               break_on_hyphens = False)
    return _wrapper


def _is_bool(obj):
    return isinstance(obj, bool)


def _is_int(obj):
    return isinstance(obj, Integral)


def _is_float(obj):
    return isinstance(obj, Real)


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


def _extremes(s):
    return min(s), max(s)


def _is_int_set(obj):
    return all(map(_is_int, obj))


def _is_contiguous(obj, min_val, max_val):
    return all([v in obj for v in range(min_val, max_val + 1)])


def _index_set(obj):
    if _is_list(obj):
        if len(obj) == 0:
            return ()
        if all(map(_is_elem, obj)):
            return _list_index_set(obj),
        if all(map(_is_array_type, obj)):
            idx_sets = list(map(_index_set, obj))
            # all children index-sets must be identical
            if idx_sets[1:] == idx_sets[:-1]:
                return (_list_index_set(obj),) + idx_sets[0]
    elif _is_dict(obj):
        if len(obj) == 0:
            return ()
        keys = obj.keys()
        if _is_int_set(keys):
            min_val, max_val = _extremes(keys)
            if _is_contiguous(keys, min_val, max_val):
                idx_set = (min_val, max_val),
                if all(map(_is_elem, obj.values())):
                    return idx_set
                if all(map(_is_array_type, obj.values())):
                    idx_sets = list(map(_index_set, obj.values()))
                    # all children index-sets must be identical
                    if idx_sets[1:] == idx_sets[:-1]:
                        return idx_set + idx_sets[0]
    raise ValueError('The input object is not a proper array: '
                     '{}'.format(repr(obj)), obj)


def _flatten_array(arr, lvl):
    if _is_dict(arr):
        arr_it = arr.values()
    else:
        arr_it = arr

    if lvl == 1:
        return arr_it

    flat_arr = []
    for sub_arr in arr_it:
        flat_arr.extend(_flatten_array(sub_arr, lvl - 1))
    return flat_arr


def _dzn_val(val):
    if isinstance(val, bool):
        return 'true' if val else 'false'
    return str(val)


def _dzn_set(s):
    if s and _is_int_set(s):
        min_val, max_val = _extremes(s)
        if _is_contiguous(s, min_val, max_val):
            return '{}..{}'.format(min_val, max_val)  # contiguous set
    return '{{{}}}'.format(', '.join(map(_dzn_val, s)))


def _index_set_str(idx_set):
    return ', '.join(['{}..{}'.format(*s) for s in idx_set])


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
        idx_set_str = _index_set_str(idx_set)
    else:
        idx_set_str = '{}' # Empty index set
    vals = []
    for i, val in enumerate(map(_dzn_val, flat_arr)):
        if i > 0:
            vals.append(', ')
        vals.append(val)

    arr_str = '[{}]'.format(''.join(vals))
    return dzn_arr.format(dim, idx_set_str, arr_str)


def _array_elem_type(arr, idx_set):
    if len(idx_set) == 0:
        return _dzn_type(arr)

    it = iter(arr.values()) if _is_dict(arr) else iter(arr)
    return _array_elem_type(next(it), idx_set[1:])


def _dzn_type(val):
    if _is_bool(val):
        return 'bool'
    if _is_int(val):
        return 'int'
    if _is_float(val):
        return 'float'
    if _is_set(val):
        if len(val) == 0:
            raise TypeError('The given set is empty.')
        return 'set of {}'.format(_dzn_type(next(iter(val))))
    if _is_array_type(val):
        idx_set = _index_set(val)
        if len(idx_set) == 0:
            raise TypeError('The given array is empty.')
        idx_set_str = _index_set_str(idx_set)
        elem_type = _array_elem_type(val, idx_set)
        return 'array[{}] of {}'.format(idx_set_str, elem_type)
    raise TypeError('Unsupported parsing for value: {}'.format(repr(val)))


def val2dzn(val, wrap=True):
    """Serializes a value (bool, int, float, set, array) into its dzn
    representation.

    Parameters
    ----------
    val
        The value to serialize
    wrap : bool
        Whether to wrap the serialized value.

    Returns
    -------
    str
        The serialized dzn representation of the given value.
    """
    if _is_value(val):
        dzn_val = _dzn_val(val)
    elif _is_set(val):
        dzn_val = _dzn_set(val)
    elif _is_array_type(val):
        dzn_val =_dzn_array_nd(val)
    else:
        raise TypeError('Unsupported parsing for value: {}'.format(repr(val)))

    if wrap:
        wrapper = _get_wrapper()
        dzn_val = wrapper.fill(dzn_val)

    return dzn_val


def stmt2dzn(name, val, declare=True, assign=True, wrap=True):
    """Returns a dzn statement declaring and assigning the given value.

    Parameters
    ----------
    val
        The value to serialize.
    declare : bool
        Whether to include the declaration of the variable in the statement or
        just the assignment.
    assign : bool
        Wheter to include assignment of the value in the statement or just the
        declaration.
    wrap : bool
        Whether to wrap the serialized value.

    Returns
    -------
    str
        The serialized dzn representation of the value.
    """
    if not (declare or assign):
        raise ValueError('The statement must be a declaration or an assignment.')

    stmt = []
    if declare:
        val_type = _dzn_type(val)
        stmt.append('{}: '.format(val_type))
    stmt.append(name)
    if assign:
        val_str = val2dzn(val, wrap=wrap)
        stmt.append(' = {}'.format(val_str))
    stmt.append(';')
    return ''.join(stmt)


def dict2dzn(objs, declare=False, assign=True, wrap=True, fout=None):
    """Serializes the objects in input and produces a list of strings encoding
    them into dzn format. Optionally, the produced dzn is written in a file.

    Supported types of objects include: str, int, float, set, list or dict.
    List and dict are serialized into dzn (multi-dimensional) arrays. The
    key-set of a dict is used as index-set of dzn arrays. The index-set of a
    list is implicitly set to 1..len(list).

    Parameters
    ----------
    objs : dict
        A dictionary containing the objects to serialize, the keys are the names
        of the variables.
    declare : bool
        Whether to include the declaration of the variable in the statements or
        just the assignment. (Default is False for backward compatibility)
    assign : bool
        Wheter to include assignment of the value in the statements or just the
        declaration.
    wrap : bool
        Whether to wrap the serialized values.
    fout : str
        Path to the output file, if None no output file is written.

    Returns
    -------
    list
        List of strings containing the dzn-encoded objects.
    """
    log = logging.getLogger(__name__)

    vals = []
    for key, val in objs.items():
        stmt = stmt2dzn(key, val, declare=declare, assign=assign, wrap=wrap)
        vals.append(stmt)

    if fout:
        log.debug('Writing file: {}'.format(fout))
        with open(fout, 'w') as f:
            for val in vals:
                f.write('{}\n\n'.format(val))
    return vals


def rebase_array(d, recursive=False):
    """Transform an indexed dictionary (such as those returned by the dzn2dict
    function when parsing arrays) into an multi-dimensional list.

    Parameters
    ----------
    d : dict
        The indexed dictionary to convert.
    bool : recursive
        Whether to rebase the array recursively.

    Returns
    -------
    list
        A multi-dimensional list.
    """
    arr = []
    min_val, max_val = _extremes(d.keys())
    for idx in range(min_val, max_val + 1):
        v = d[idx]
        if recursive and _is_dict(v):
            v = rebase_array(v)
        arr.append(v)
    return arr

