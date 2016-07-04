import re
import logging

from pymzn.dzn import dzn_value

_stmt_p = re.compile("(?:^|;)\s*([^;]+)")
_comm_p = re.compile("%.+?\n")
_var_p = re.compile("^\s*([^:]+?):\s*([^=]+)\s*(?:=\s*(.+))?$")
_var_type_p = re.compile('^\s*.*?var.+')
_array_type_p = re.compile('^\s*array\[([\w\.]+(?:\s*,\s*[\w\.]+)*)\]'
                           '\s*of\s*(.+?)$')
_output_stmt_p = re.compile('output\.+;', re.DOTALL)
_solve_stmt_p = re.compile('solve\.+;', re.DOTALL)


class MiniZincModel(object):
    """
    Wraps a minizinc model.

    Can use a mzn file as template and add variables, constraints and modify
    the solve statement. The output statement can be replaced by a
    pymzn-friendly one when using the minizinc function.
    The final model is a string combining the existing model (if provided)
    and the updates performed on the MinizincModel instance.
    """

    def __init__(self, mzn=None, output_vars=None, *,
                 replace_output_stmt=True):
        """
        :param str or MiniZincModel mzn: The minizinc problem template.
                                         It can be either a string or an
                                         instance of MinizincModel. If it is
                                         a string, it can be either the path
                                         to the mzn file or the content of
                                         the model.
        :param [str] output_vars: The list of output variables. If not
                                  provided, the default list is the list of
                                  free variables in the model, i.e. those
                                  variables that are declared but not
                                  defined in the model
        :param bool replace_output_stmt: Whether to replace the output
                                         statement with the pymzn default
                                         one (used to parse the solutions
                                         with solns2out with the default
                                         parser)
        """
        self.mzn = mzn
        self.mzn_out_file = ''
        self.output_vars = output_vars if output_vars else []
        self.replace_output_stmt = replace_output_stmt
        self.vars = {}
        self._free_vars = set()
        self.constraints = []
        self.solve_stmt = None
        self._array_dim = {}
        self._log = logging.getLogger(__name__)

    def constraint(self, constr, comment=None):
        """
        Adds a constraint to the current model.

        :param str constr: The content of the constraint, i.e. only the actual
                           constraint without the starting 'constraint' and
                           the ending semicolon
        :param str comment: A comment to attach to the constraint
        """
        self.constraints.append((constr, comment))

    def solve(self, solve_stmt, comment=None):
        """
        Updates the solve statement of the model.

        :param str solve_stmt: The content of the solve statement, i.e. only
                               the solving expression (and possible
                               annotations) without the starting 'solve' and
                               the ending semicolon
        :param str comment: A comment to attach to the statement
        """
        self.solve_stmt = (solve_stmt, comment)

    def var(self, vartype, var, val=None, comment=None):
        """
        Adds a variable (or parameter) to the model.

        :param str vartype: The type of the variable (in the minizinc
                            language), including 'var' if a variable.
        :param str var: The name of the variable
        :param any val: The value of the variable if any. It can be any value
                        convertible to dzn through the dzn_value function
        :param str comment: A comment to attach to the variable declaration
                            statement
        """
        self.vars[var] = (vartype, dzn_value(val), comment)
        if _var_type_p.match(vartype) and val is None:
            self._free_vars.add(var)
        _array_type_m = _array_type_p.match(vartype)
        if _array_type_m:
            dim = len(_array_type_m.group(1).split(','))
            self._array_dim[var] = dim

    def _dzn_output_stmt(self):
        out_var = '"{0} = ", show({0}), ";\\n"'
        out_array = '"{0} = array{1}d(", {2}, ", ", show({0}), ");\\n"'
        out_list = []
        for var in self.output_vars:
            if var in self._array_dim:
                dim = self._array_dim[var]
                if dim == 1:
                    show_idx_sets = 'show(index_set({}))'.format(var)
                else:
                    show_idx_sets = []
                    for d in range(1, dim + 1):
                        show_idx_sets.append('show(index_set_{}of{}'
                                             '({}))'.format(d, dim, var))
                    show_idx_sets = ', ", ", '.join(show_idx_sets)
                out_list.append(out_array.format(var, dim, show_idx_sets))
            else:
                out_list.append(out_var.format(var))
        out_list = ', '.join(out_list)
        return ''.join(['output [ ', out_list, ' ];'])

    def compile(self):
        """
        Compiles the model. The compiled model contains the content of the
        template (if provided) plus the added variables and constraints. The
        solve statement will be replaced if provided a new one and the
        output statement will be replaced with a pymzn-friendly one if
        replace_output_stmt=True.

        :return: A string containing the compiled model.
        """
        model = ""
        gen = True

        if self.mzn:
            if isinstance(self.mzn, str):
                if self.mzn.endswith('.mzn'):
                    with open(self.mzn) as f:
                        model = f.read()
                    self.mzn_out_file = self.mzn
                else:
                    model = self.mzn
                    self.mzn_out_file = 'mznout.mzn'
            elif isinstance(self.mzn, MiniZincModel):
                model = self.mzn.compile()
                self.mzn_out_file = self.mzn.mzn_out_file
                gen = False
            else:
                self._log.warning('The provided value for file_mzn is valid. '
                                  'It will be ignored.')

        stmts = _stmt_p.findall(model)
        for stmt in stmts:
            stmt = _comm_p.sub('', stmt)
            _var_m = _var_p.match(stmt)
            if _var_m:
                vartype = _var_m.group(1)
                var = _var_m.group(2)
                val = _var_m.group(3)
                if _var_type_p.match(vartype) and val is None:
                    self._free_vars.add(var)
                _array_type_m = _array_type_p.match(vartype)
                if _array_type_m:
                    dim = len(_array_type_m.group(1).split(','))
                    self._array_dim[var] = dim

        lines = ['\n%% GENERATED BY PYMZN %%\n\n'] if gen else ['\n\n\n']

        for var, (vartype, val, comment) in self.vars.items():
            comment and lines.append('% {}'.format(comment))
            if val is not None:
                lines.append('{}: {} = {};'.format(vartype, var, val))
            else:
                lines.append('{}: {};'.format(vartype, var))

        lines.append('\n')
        for i, (constr, comment) in self.constraints:
            comment and lines.append('% {}'.format(comment))
            lines.append('constraint {};'.format(constr))

        if self.solve_stmt is not None:
            model = _solve_stmt_p.sub('', model)
            solve_stmt, comment = self.solve_stmt
            lines.append('\n')
            comment and lines.append('% {}'.format(comment))
            lines.append('solve {};'.format(solve_stmt))

        if not self.output_vars:
            self.output_vars.extend(self._free_vars)

        if self.replace_output_stmt:
            model = _output_stmt_p.sub('', model)
            lines.append('\n')
            output_stmt = self._dzn_output_stmt()
            lines.append(output_stmt)
            lines.append('\n')

        model += '\n'.join(lines)
        return model
