import logging
import os.path
import re

import itertools

from pymzn.dzn import dzn_value

_minizinc_instance_counter = itertools.count()


class MiniZincModel(object):
    """
    Wraps a minizinc model.

    It can use a mzn file as template and add variables, constraints and
    modify the solve statement. The output statement can be replaced by a
    pymzn-friendly one when using the minizinc function.
    The final model is a string combining the existing _model (if provided)
    and the updates performed on the MinizincModel instance.
    """

    _stmt_p = re.compile('(?:^|;)\s*([^;]+)')
    _comm_p = re.compile('%.+?\n')
    _var_p = re.compile('^\s*([^:]+?):\s*([^=]+)\s*(?:=\s*(.+))?$')
    _var_type_p = re.compile('^\s*.*?var.+')
    _array_type_p = re.compile('^\s*array\[([\w\.]+(?:\s*,\s*[\w\.]+)*)\]'
                               '\s+of\s+(.+?)$')
    _output_stmt_p = re.compile('(^|\s)output\s[^;]+?;')
    _solve_stmt_p = re.compile('(^|\s)solve\s[^;]+?;')

    def __init__(self, mzn=None, *, output_base=None, serialize=False):
        """
        :param str mzn: The minizinc problem template.
                        It can be either a string or an instance of
                        MiniZincModel. If it is a string, it can be either
                        the path to the mzn file or the content of the model.
        """
        self._log = logging.getLogger(__name__)
        if mzn:
            base, ext = os.path.splitext(mzn)
            if ext != '.mzn':
                self._model = mzn
                self._write_model = True
                self._mzn_file = None
                base = 'mznout'
            else:
                self._model = None
                self._write_model = output_base is not None
                self._mzn_file = mzn
            self._output_base = output_base if output_base else base
        else:
            self._model = None
            self._write_model = False
            self._mzn_file = None
            self._output_base = output_base if output_base else 'mznout'

        self.serialize = serialize
        self.vars = {}
        self.constraints = []
        self.solve_stmt = None
        self.output_stmt = None
        self._free_vars = set()
        self._array_dims = {}
        self._modified = False

    def constraint(self, constr, comment=None):
        """
        Adds a constraint to the current model.

        :param str constr: The content of the constraint, i.e. only the actual
                           constraint without the starting 'constraint' and
                           the ending semicolon
        :param str comment: A comment to attach to the constraint
        """
        self.constraints.append((constr, comment))
        self._modified = True

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
        self._modified = True

    def output(self, output_stmt, comment=None):
        """
        Updates the output statement of the model.

        :param str output_stmt: The content of the output statement, i.e.
                                only the output list (excluding the square
                                brackets) without the starting 'output'
                                and the ending semicolon
        :param str comment: A comment to attach to the statement
        """
        self.output_stmt = (output_stmt, comment)
        self._modified = True

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
        val = dzn_value(val) if val else None
        self.vars[var] = (vartype, val, comment)
        if self._var_type_p.match(vartype) and val is None:
            self._free_vars.add(var)
        _array_type_m = self._array_type_p.match(vartype)
        if _array_type_m:
            dim = len(_array_type_m.group(1).split(','))
            self._array_dims[var] = dim
        self._modified = True

    def _load_model(self):
        if self._model is None:
            if self._mzn_file:
                with open(self._mzn_file) as f:
                    self._model = f.read()
            else:
                self._model = ''
        return self._model

    def _parse_model_stmts(self):
        model = self._load_model()
        stmts = self._stmt_p.findall(model)
        for stmt in stmts:
            stmt = self._comm_p.sub('', stmt)
            _var_m = self._var_p.match(stmt)
            if _var_m:
                vartype = _var_m.group(1)
                var = _var_m.group(2)
                val = _var_m.group(3)
                if self._var_type_p.match(vartype) and val is None:
                    self._free_vars.add(var)
                _array_type_m = self._array_type_p.match(vartype)
                if _array_type_m:
                    dim = len(_array_type_m.group(1).split(','))
                    self._array_dims[var] = dim

    def dzn_output_stmt(self, output_vars=None, comment=None):
        """
        Sets the output statement to be a dzn representation of output_vars.
        If output_var is not provided (= None) then the free variables of
        the model are used i.e. those variables that are declared but not
        defined in the model (not depending on other variables).

        :param [str] output_vars: The list of output variables.
        :param str comment: A comment to attach to the statement
        """

        # Look for free variables and array dimensions in the model statements
        self._parse_model_stmts()

        # Set output vars to the free variables if None provided
        if not output_vars:
            output_vars = list(self._free_vars)

        # Build the output statement from the output variables
        out_var = '"{0} = ", show({0}), ";\\n"'
        out_array = '"{0} = array{1}d(", {2}, ", ", show({0}), ");\\n"'
        out_list = []
        for var in output_vars:
            if var in self._array_dims:
                dim = self._array_dims[var]
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
        self.output(out_list, comment)

    def compile(self):
        """
        Compiles the _model. The compiled _model contains the content of the
        template (if provided) plus the added variables and constraints. The
        solve statement will be replaced if provided a new one and the
        output statement will be replaced with a pymzn-friendly one if
        replace_output_stmt=True.

        :return: A string containing the compiled _model.
        """

        if not (self._write_model or self._modified):
            if not self._mzn_file:
                raise RuntimeError('Cannot compile an empty model.')
            return self._mzn_file

        # if serialize or not supposed to write but modified
        if self.serialize or (self._modified and not self._write_model):
            # Ensures isolation of instances and thread safety
            sid = next(_minizinc_instance_counter)
            output_file = '{}_{}.mzn'.format(self._output_base, sid)
        else:
            output_file = self._output_base + '.mzn'

        model = self._load_model()

        if self._modified:
            lines = ['\n\n\n%%% GENERATED BY PYMZN %%%\n\n']

            for var, (vartype, val, comment) in self.vars.items():
                comment and lines.append('% {}'.format(comment))
                if val is not None:
                    lines.append('{}: {} = {};'.format(vartype, var, val))
                else:
                    lines.append('{}: {};'.format(vartype, var))

            for i, (constr, comment) in self.constraints:
                comment and lines.append('% {}'.format(comment))
                lines.append('constraint {};'.format(constr))

            if self.solve_stmt is not None:
                model = self._solve_stmt_p.sub('', model)
                solve_stmt, comment = self.solve_stmt
                comment and lines.append('% {}'.format(comment))
                lines.append('solve {};'.format(solve_stmt))

            if self.output_stmt is not None:
                model = self._output_stmt_p.sub('', model)
                output_stmt, comment = self.solve_stmt
                comment and lines.append('% {}'.format(comment))
                lines.append('output [{}];'.format(output_stmt))
            model += '\n'.join(lines)

        with open(output_file, 'w') as f:
            f.write(model)

        return output_file
