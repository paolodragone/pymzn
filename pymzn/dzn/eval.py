# -*- coding: utf-8 -*-

import re
import os.path

from .marsh import rebase_array

# boolean pattern
_bool_p = re.compile('^(?:true|false)$')

# integer pattern
_int_p = re.compile('^[+\-]?\d+$')

# float pattern
_float_p = re.compile('^[+\-]?\d*\.\d+(?:[eE][+\-]?\d+)?$')

# contiguous integer set pattern
_cont_int_set_p = re.compile('^([+\-]?\d+)\.\.([+\-]?\d+)$')

# integer set pattern
_int_set_p = re.compile('^(\{(?P<vals>[\d\s,+\-]*)\})$')

# matches any of the previous
_val_p = re.compile('(?:true|false|\{(?:[\d ,+\-]+)\}'
                    '|(?:[+\-]?\d+)\.\.(?:[+\-]?\d+)'
                    '|[+\-]?\d*\.\d+(?:[eE][+\-]?\d+)?'
                    '|[+\-]?\d+)')

# multi-dimensional array pattern
_array_p = re.compile('^\s*(?:array(?P<dim>\d)d\s*\(\s*'
                      '(?P<indices>([\d\.+\-]+|\{\})'
                      '(?:\s*,\s*([\d\.+\-]+|\{\}))*)\s*,\s*)?'
                      '\[(?P<vals>[\w\s\.,+\-\\\/\*^|\(\)\{\}]*)\]\)?$')

# ratio pattern (used in OptiMathSat)
_ratio_p = re.compile('^\s*(?P<numerator>\d+)/(?P<denominator>\d+)$')

# variable pattern
_var_p = re.compile('^\s*(?P<var>[\w]+)\s*=\s*(?P<val>.+)$', re.DOTALL)

# statement pattern
_stmt_p = re.compile('\s*([^;]+?);')

# comment pattern
_comm_p = re.compile('%.+?\n')


def _eval_array(indices, vals, rebase_arrays=True):
    # Recursive evaluation of multi-dimensional arrays returned by the solns2out
    # utility of the type: array2d(2..4, 1..3, [1, 2, 3, 4, 5, 6, 7, 8, 9])
    idx_set = indices[0]
    if len(indices) == 1:
        arr = {i: _eval_val(vals.pop(0)) for i in idx_set}
    else:
        arr = {i: _eval_array(indices[1:], vals) for i in idx_set}

    if rebase_arrays and list(idx_set)[0] == 1:
        arr = rebase_array(arr)

    return arr


def _eval_indices(st):
    # Parse indices of multi-dimensional arrays
    ss = st.strip().split(',')
    indices = []
    for s in ss:
        s = s.strip()
        cont_int_set_m = _cont_int_set_p.match(s)
        if cont_int_set_m:
            v1 = int(cont_int_set_m.group(1))
            v2 = int(cont_int_set_m.group(2))
            indices.append(range(v1, v2 + 1))
        elif s == '{}':
            indices.append([])
        else:
            raise ValueError('Index \'{}\' is not well formatted.'.format(s))
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
            raise ValueError('A value of the input set is not an integer: '
                             '{}'.format(repr(p_val)), p_val)
    return p_s


def _eval_val(val):
    # boolean value
    if _bool_p.match(val):
        return {'true': True, 'false': False}[val]

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
        return set(range(v1, v2 + 1))

    # integer set
    set_m = _int_set_p.match(val)
    if set_m:
        vals = set_m.group('vals')
        if vals:
            return _eval_set(vals.split(','))
        return set()
    return None


def dzn2dict(dzn, *, rebase_arrays=True):
    """Evaluates a dzn string or file into a Python dictionary of variable
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
    if dzn_ext == '.dzn':
        with open(dzn) as f:
            dzn = f.read()

    assign = {}
    stmts = _stmt_p.findall(dzn)
    for stmt in stmts:
        stmt = _comm_p.sub('', stmt)
        var_m = _var_p.match(stmt)
        if var_m:
            var = var_m.group('var')
            val = var_m.group('val')
            p_val = _eval_val(val)
            if p_val is not None:
                assign[var] = p_val
                continue

            array_m = _array_p.match(val)
            if array_m:
                vals = array_m.group('vals')
                vals = _val_p.findall(vals)
                dim = array_m.group('dim')
                if dim:  # explicit dimensions
                    dim = int(dim)
                    indices = array_m.group('indices')
                    indices = _eval_indices(indices)
                    assert len(indices) == dim
                else:  # assuming 1d array based in 1
                    indices = [range(1, len(vals) + 1)]
                if len(vals) == 0:
                    p_val = []
                else:
                    p_val = _eval_array(indices, vals, rebase_arrays)
                assign[var] = p_val
                continue

            ratio_m = _ratio_p.match(val)
            if ratio_m:
                num = float(ratio_m.group('numerator'))
                den = float(ratio_m.group('denominator'))
                assign[var] = num / den
                continue
        raise ValueError('Unsupported evaluation for statement:\n'
                         '{}'.format(repr(stmt)))
    return assign

