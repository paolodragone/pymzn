# -*- coding: utf-8 -*-

from __future__ import with_statement
from __future__ import absolute_import
import re
import os.path

from .marsh import rebase_array
from io import open

# boolean pattern
_bool_p = re.compile(u'^(?:true|false)$')

# integer pattern
_int_p = re.compile(u'^[+\-]?\d+$')

# float pattern
_float_p = re.compile(u'^[+\-]?\d*\.\d+(?:[eE][+\-]?\d+)?$')

# contiguous integer set pattern
_cont_int_set_p = re.compile(u'^([+\-]?\d+)\.\.([+\-]?\d+)$')

# integer set pattern
_int_set_p = re.compile(u'^(\{(?P<vals>[\d\s,+\-]*)\})$')

# matches any of the previous
_val_p = re.compile(u'(?:true|false|\{(?:[\d ,+\-]+)\}'
                    u'|(?:[+\-]?\d+)\.\.(?:[+\-]?\d+)'
                    u'|[+\-]?\d*\.\d+(?:[eE][+\-]?\d+)?'
                    u'|[+\-]?\d+)')

# multi-dimensional array pattern
_array_p = re.compile(u'^\s*(?:array(?P<dim>\d)d\s*\(\s*'
                      u'(?P<indices>([\d\.+\-]+|\{\})'
                      u'(?:\s*,\s*([\d\.+\-]+|\{\}))?)\s*,\s*)?'
                      u'\[(?P<vals>[\w\s\.,+\-\\\/\*^|\(\)\{\}]*)\]\)?$')

# variable pattern
_var_p = re.compile(u'^\s*(?P<var>[\w]+)\s*=\s*(?P<val>.+)$', re.DOTALL)

# statement pattern
_stmt_p = re.compile(u'\s*([^;]+?);')

# comment pattern
_comm_p = re.compile(u'%.+?\n')


def _eval_array(indices, vals, rebase_arrays=True):
    # Recursive evaluation of multi-dimensional arrays returned by the solns2out
    # utility of the type: array2d(2..4, 1..3, [1, 2, 3, 4, 5, 6, 7, 8, 9])
    idx_set = indices[0]
    if len(indices) == 1:
        arr = dict((i, _eval_val(vals.pop(0))) for i in idx_set)
    else:
        arr = dict((i, _eval_array(indices[1:], vals)) for i in idx_set)

    if rebase_arrays and list(idx_set)[0] == 1:
        arr = rebase_array(arr)

    return arr


def _eval_indices(st):
    # Parse indices of multi-dimensional arrays
    ss = st.strip().split(u',')
    indices = []
    for s in ss:
        s = s.strip()
        cont_int_set_m = _cont_int_set_p.match(s)
        if cont_int_set_m:
            v1 = int(cont_int_set_m.group(1))
            v2 = int(cont_int_set_m.group(2))
            indices.append(xrange(v1, v2 + 1))
        elif s == u'{}':
            indices.append([])
        else:
            raise ValueError(u'Index \'{}\' is not well formatted.'.format(s))
    return indices


def _eval_set(vals):
    # Parse sets of integers of the type: {41, 2, 53, 12, 8}
    p_s = set()
    for val in vals:
        p_val = val.strip()
        if _int_p.match(p_val):
            p_val = int(p_val)
            p_s.add(p_val)
        else:
            raise ValueError(u'A value of the input set is not an integer: '
                             u'{}'.format(repr(p_val)), p_val)
    return p_s


def _eval_val(val):
    # boolean value
    if _bool_p.match(val):
        return {u'true': True, u'false': False}[val]

    # integer value
    if _int_p.match(val):
        return int(val)

    # float value
    if _float_p.match(val):
        return float(val)

    # contiguous integer set
    cont_int_set_m = _cont_int_set_p.match(val)
    if cont_int_set_m:
        v1 = int(cont_int_set_m.group(1))
        v2 = int(cont_int_set_m.group(2))
        return set(xrange(v1, v2 + 1))

    # integer set
    set_m = _int_set_p.match(val)
    if set_m:
        vals = set_m.group(u'vals')
        if vals:
            return _eval_set(vals.split(u','))
        return set()
    return None


def dzn2dict(dzn, **_3to2kwargs):
    if 'rebase_arrays' in _3to2kwargs: rebase_arrays = _3to2kwargs['rebase_arrays']; del _3to2kwargs['rebase_arrays']
    else: rebase_arrays = True
    u"""Evaluates a dzn string or file into a Python dictionary of variable
    assignments.

    Parameters
    ----------
    dzn : str
        A dzn content string or a path to a dzn file.
    rebase_arrays : bool
        Whether to return arrays as zero-based lists or to return them as
        dictionaries, preserving the original index-sets.

    Returns
    -------
    dict
        A dictionary containing the variable assignments evaluated from the
        input file or string.
    """
    dzn_ext = os.path.splitext(dzn)[1]
    if dzn_ext == u'.dzn':
        with open(dzn) as f:
            dzn = f.read()

    assign = {}
    stmts = _stmt_p.findall(dzn)
    for stmt in stmts:
        stmt = _comm_p.sub(u'', stmt)
        var_m = _var_p.match(stmt)
        if var_m:
            var = var_m.group(u'var')
            val = var_m.group(u'val')
            p_val = _eval_val(val)
            if p_val is not None:
                assign[var] = p_val
                continue

            array_m = _array_p.match(val)
            if array_m:
                vals = array_m.group(u'vals')
                vals = _val_p.findall(vals)
                dim = array_m.group(u'dim')
                if dim:  # explicit dimensions
                    dim = int(dim)
                    indices = array_m.group(u'indices')
                    indices = _eval_indices(indices)
                    assert len(indices) == dim
                else:  # assuming 1d array based in 1
                    indices = [xrange(1, len(vals) + 1)]
                if len(vals) == 0:
                    p_val = []
                else:
                    p_val = _eval_array(indices, vals, rebase_arrays)
                assign[var] = p_val
                continue
        raise ValueError(u'Unsupported evaluation for statement:\n'
                         u'{}'.format(repr(stmt)))
    return assign

