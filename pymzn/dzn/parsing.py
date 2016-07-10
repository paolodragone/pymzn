import re

from pymzn import rebase_array


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
_array_p = re.compile(('^\s*(?:array(?P<dim>\d)d\s*\(\s*'
                       '(?P<indices>[\d\.+\-](?:\s*,\s*[\d\.+\-]+)?)\s*,\s*)?'
                       '\[(?P<vals>[\w \.,+\-\\\/\*^|\(\)\{\}]+)\]\)?$'))

# variable pattern
_var_p = re.compile('^\s*(?P<var>[\w]+)\s*=\s*(?P<val>.+)$')

# statement pattern
_stmt_p = re.compile('(?:^|;)\s*([^;]+)')

# comment pattern
_comm_p = re.compile('%.+?\n')


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


def parse_dzn(dzn, *, rebase_arrays=True):
    """
    Parse one or more pieces of dzn strings.

    :param str or [str] dzn: A dzn string or a list of dzn strings
    :param bool rebase_arrays: Whether to return arrays as zero-based lists
                               or to return them as dictionaries, thereby
                               preserving the index-sets.
    :return: A list of dictionaries containing the variable assignments
             parsed from the inputs
    :rtype: [dict]
    """
    # log = logging.getLogger(__name__)
    soln = {}
    stmts = _stmt_p.findall(dzn)
    for stmt in stmts:
        stmt = _comm_p.sub('', stmt)
        # log.debug('Parsing stmt: %s', stmt)
        var_m = _var_p.match(stmt)
        if var_m:
            var = var_m.group('var')
            val = var_m.group('val')
            p_val = _parse_val(val)
            if p_val is not None:
                soln[var] = p_val
                # log.debug('Parsed value: %s', p_val)
                continue

            # log.debug('Parsing array: %s', val)
            array_m = _array_p.match(val)
            if array_m:
                vals = array_m.group('vals')
                vals = _val_p.findall(vals)
                dim = array_m.group('dim')
                if dim:  # explicit dimensions
                    dim = int(dim)
                    indices = array_m.group('indices')
                    # log.debug('Parsing indices: %s', indices)
                    indices = _parse_indices(indices)
                    assert len(indices) == dim
                    # log.debug('Parsing values: %s', vals)
                    p_val = _parse_array(indices, vals)
                else:  # assuming 1d array based on 0
                    # log.debug('Parsing values: %s', vals)
                    p_val = _parse_array([range(len(vals))], vals)
                if rebase_arrays:
                    p_val = rebase_array(p_val)
                soln[var] = p_val
                # log.debug('Parsed array: %s', p_val)
                continue
        raise ValueError('Unsupported parsing for stmt:\n{}'.format(stmt))
    return soln
