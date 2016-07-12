from numbers import Integral, Number
from collections.abc import Set, Sized, Iterable, Mapping


__all__ = ['dzn', 'dzn_value', 'rebase_array']


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


def rebase_array(d):
    """
    Transform an indexed dictionary (such as those returned by the parse_dzn
    function when parsing arrays) into an multi-dimensional list.

    :param dict d: The indexed dictionary to convert
    :return: A multi-dimensional list
    :rtype: list
    """
    arr = []
    min_val, max_val = _dict_index_set(d)
    idx_set = range(min_val, max_val + 1)
    for idx in idx_set:
        v = d[idx]
        if _is_dict(v):
            v = rebase_array(v)
        arr.append(v)
    return arr
