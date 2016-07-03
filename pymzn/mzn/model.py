import re
import logging

from pymzn.dzn import dzn_value

_output_stmt_p = re.compile('output.+?;', re.S)
_free_var_p = re.compile('.+?var[^:]+?:\s*(\w+)\s*;', re.S)
_free_var_type_p = re.compile('.+?var.+?', re.S)
_solve_stmt_p = re.compile('solve.+?;', re.S)


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
        self.constraints = []
        self.solve_stmt = None
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

    @staticmethod
    def _pymzn_output_stmt(output_vars):
        out_var = '"\'{0}\':", show({0})'
        out_list = ', '.join([out_var.format(var) for var in output_vars])
        return ''.join(['output [ "{", ', out_list, ' "}" ];'])

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
                gen = False
            else:
                self._log.warning('The provided value for file_mzn is valid. '
                                  'It will be ignored.')

        if not self.output_vars:
            free_vars = _free_var_p.findall(model)
            self.output_vars.append(free_vars)

        lines = ['\n%% GENERATED BY PYMZN %%\n\n'] if gen else ['\n\n\n']

        for var, (vartype, val, comment) in self.vars.items():
            comment and lines.append('% {}'.format(comment))
            if val is not None:
                lines.append('{}: {} = {};'.format(vartype, var, val))
            else:
                lines.append('{}: {};'.format(vartype, var))
                if _free_var_type_p.match(vartype):
                    self.output_vars.append(var)

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
            raise RuntimeError('The model has no output variable.')

        if self.replace_output_stmt:
            model = _output_stmt_p.sub('', model)
            lines.append('\n')
            output_stmt = self._pymzn_output_stmt(self.output_vars)
            lines.append(output_stmt)
            lines.append('\n')

        model += '\n'.join(lines)
        return model
