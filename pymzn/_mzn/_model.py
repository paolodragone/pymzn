# -*- coding: utf-8 -*-
"""PyMzn can also be used to dynamically change a model during runtime. For
example, it can be useful to add constraints incrementally or change the solving
statement dynamically. To dynamically modify a model, you can use the class
``MiniZincModel``, which can take an optional model file as input which can then
be modified by adding variables and constraints, and by modifying the solve or
output statements. An instance of ``MiniZincModel`` can then be passed directly
to the ``minizinc`` function to be solved.
::

    model = pymzn.MiniZinModel('test.mzn')

    for i in range(10):
        model.add_constraint('arr_1[i] < arr_2[i]')
        pymzn.minizinc(model)
"""

import re
import os.path

from pymzn import dzn_value
from pymzn._utils import get_logger
from pymzn._dzn._marsh import dzn_statement


_stmt_p = re.compile('(?:^|;)\s*([^;]+)')
_comm_p = re.compile('%.*\n')
_var_p = re.compile('^\s*([^:]+?):\s*(\w+)\s*(?:=\s*(.+))?$')
_var_type_p = re.compile('^\s*.*?var.+')
_array_type_p = re.compile('^\s*array\[([\w\.]+(?:\s*,\s*[\w\.]+)*)\]'
                            '\s+of\s+(.+?)$')
_output_stmt_p = re.compile('(^|\s)output\s*\[.+?\]\s*;', re.DOTALL)
_solve_stmt_p = re.compile('(^|\s)solve\s[^;]+?;')


class Statement(object):
    """A statement of a MiniZincModel.

    Attributes
    ----------
    stmt : str
        The statement string.
    comment : str
        An optional comment to attach to the statement.
    """
    def __init__(self, stmt, comment=None):
        self.stmt = stmt
        self.comment = comment

    def compile(self):
        """Compiles the statement.

        Returns
        -------
        str
            The statement string plus an optional comment attached.
        """
        s = ''
        if self.comment:
            s += '% {}\n'.format(self.comment)
        s += self.stmt
        return s


class Constraint(Statement):
    """A constraint statement.

    Attributes
    ----------
    const : str
        The content of the constraint, i.e. only the actual constraint without
        the starting 'constraint' and the ending semicolon.
    comment : str
        A comment to attach to the constraint.
    """
    def __init__(self, const, comment=None):
        self.const = const
        stmt = 'constraint {};'.format(self.const)
        super().__init__(stmt, comment)


class Parameter(Statement):
    """A parameter statement.

    Attributes
    ----------
    name : str
        The name of the parameter.
    val
        The python object to convert into a parameter. The type is inferred from
        the python object.
    assign : bool
        If True the parameter value will be assigned directly into the model,
        otherwise it will only be declared in the model and then it will have to
        be assigned in the data.
    comment : str
        A comment to attach to the variable statement.
    """
    def __init__(self, name, val, assign=True, comment=None):
        stmt = dzn_statement(name, val, assign=assign)
        super().__init__(stmt, comment)


class Variable(Statement):
    """A variable statement.

    Attributes
    ----------
    vartype : str
        The type of the variable.
    var : str
        The name of the variable.
    val : str
        The optional value of the variable statement.
    output : bool
        Whether the variable is an output variable.
    comment : str
        A comment to attach to the variable statement.
    """
    def __init__(self, vartype, var, val=None, output=False, comment=None):
        self.vartype = vartype
        self.var = var
        self.val = val
        self.output = output

        stmt = '{} : {}'.format(self.vartype, self.var)
        if self.val:
            stmt += ' = {}'.format(self.val)
        if output:
            _array_type_m = _array_type_p.match(vartype)
            if _array_type_m:
                indexset = _array_type_m.group(1)
                stmt += ' :: output_array([{}])'.format(indexset)
            else:
                stmt += ' :: output_var'
        stmt += ';'

        super().__init__(stmt, comment)


class ArrayVariable(Variable):
    """An array variable statement.

    Attributes
    ----------
    indexset : str
        The indexset of the array.
    domain : str
        The domain of the array.
    var : str
        The name of the variable.
    val : str
        The optional value of the variable statement.
    output : bool
        Whether the array variable is an output array.
    comment : str
        A comment to attach to the variable statement.
    """
    def __init__(self, indexset, domain, var, val=None, output=False,
                 comment=None):
        self.indexset = indexset
        self.domain = domain
        vartype = 'array[{}] of var {}'.format(self.indexset, self.domain)
        super().__init__(vartype, var, val, output, comment)


class OutputStatement(Statement):
    """An output statement.

    Attributes
    ----------
    output : str
        The content of the output statement, i.e. only the actual output without
        the starting 'output', the square brackets and the ending semicolon.
    comment : str
        A comment to attach to the output statement.
    """
    def __init__(self, output, comment=None):
        self.output = output
        stmt = 'output [{}];'.format(self.output)
        super().__init__(stmt, comment)


class SolveStatement(Statement):
    """A solve statement.

    Attributes
    ----------
    solve : str
        The content of the solve statement, i.e. only the actual solve without
        the starting 'solve' and the ending semicolon.
    comment : str
        A comment to attach to the solve statement.
    """

    def __init__(self, solve, comment=None):
        self.solve = solve
        stmt = 'solve {};'.format(self.solve)
        super().__init__(stmt, comment)


class MiniZincModel(object):
    """Mutable class representing a MiniZinc model.

    It can use a mzn file as template, add variables and constraints,
    modify the solve and output statements. The output statement can also be
    replaced by a dzn representation of a list of output variables.
    The final model is a string combining the existing model (if provided)
    and the updates performed on the MiniZincModel instance.

    Parameters
    ----------
    mzn : str
        The content or the path to the template mzn file.
    """
    def __init__(self, mzn=None):
        self._statements = []
        self._solve_stmt = None
        self._output_stmt = None
        self._free_vars = set()
        self._array_dims = {}
        self._modified = False
        self._parsed = False

        if mzn and isinstance(mzn, str):
            if os.path.isfile(mzn):
                self.mzn_file = mzn
                self.model = None
            else:
                self.mzn_file = None
                self.model = mzn
        else:
            self.mzn_file = None
            self.model = None

    def constraint(self, constr, comment=None):
        """Adds a constraint to the current model.

        Parameters
        ----------
        constr : str or Constraint
            As a string, the content of the constraint, i.e. only the actual
            constraint without the starting 'constraint' and the ending
            semicolon.
        comment : str
            A comment to attach to the constraint.
        """
        if not isinstance(constr, Constraint):
            constr = Constraint(constr, comment)
        self._statements.append(constr)
        self._modified = True

    def constraints(self, constrs):
        """Add a list of constraints.

        Parameters
        ----------
        constrs : list of str or Constraint
            A list of constraints.
        """
        for constr in constrs:
            self.constraint(constr)

    def solve(self, solve_stmt, comment=None):
        """Updates the solve statement of the model.

        Parameters
        ----------
        solve_stmt : str
            The content of the solve statement, i.e. only the actual solve
            without the starting 'solve' and the ending semicolon.
        comment : str
            A comment to attach to the solve statement.
        """
        if not isinstance(solve_stmt, SolveStatement):
            solve_stmt = SolveStatement(solve_stmt, comment)
        self._solve_stmt = solve_stmt
        self._modified = True

    def satisfy(self, comment=None):
        """ Shorthand for solve('satisfy') """
        self._solve_stmt = SolveStatement('satisfy', comment)
        self._modified = True

    def maximize(self, expr, comment=None):
        """ Shorthand for solve('maximize ' + expr) """
        self._solve_stmt = SolveStatement('maximize ' + expr, comment)
        self._modified = True

    def minimize(self, expr, comment=None):
        """ Shorthand for solve('minimize ' + expr) """
        self._solve_stmt = SolveStatement('minimize ' + expr, comment)
        self._modified = True

    def output(self, output_stmt, comment=None):
        """Updates the output statement of the model.

        Parameters
        ----------
        solve_stmt : str
            The content of the output statement, i.e. only the actual output
            without the starting 'output', the square brackets and the ending
            semicolon.
        comment : str
            A comment to attach to the output statement.
        """
        if not isinstance(output_stmt, OutputStatement):
            output_stmt = OutputStatement(output_stmt, comment)
        self._output_stmt = output_stmt
        self._modified = True

    def par(self, name, val, assign=True, comment=None):
        """Adds a parameter to the model.

        Parameters
        ----------
        name
            The name of the parameter.
        val : obj
            The python object to add as a parameter to the model.
        assign : bool
            If True the parameter value will be assigned directly into the
            model, otherwise it will only be declared in the model and then it
            will have to be assigned in the data.
        comment : str
            A comment to attach to the parameter statement.
        """
        par = Parameter(name, val, assign=assign, comment=comment)
        self._statements.append(par)
        self._modified = True

    def var(self, vartype, var, val=None, output=False, comment=None):
        """Adds a variable to the model.

        Parameters
        ----------
        vartype : str
            The type of the variable.
        var : str
            The name of the variable.
        val : str
            The optional value of the variable statement.
        output : bool
            Whether the variable is an output variable.
        comment : str
            A comment to attach to the variable statement.
        """
        val = dzn_value(val) if val is not None else None
        self._statements.append(Variable(vartype, var, val, output, comment))
        if output or _var_type_p.match(vartype) and val is None:
            self._free_vars.add(var)
        _array_type_m = _array_type_p.match(vartype)
        if _array_type_m:
            dim = len(_array_type_m.group(1).split(','))
            self._array_dims[var] = dim
        self._modified = True

    def array_var(self, indexset, domain, var, val=None, output=False,
                  comment=None):
        """Adds an array variable to the model.

        Parameters
        ----------
        indexset : str
            The indexset of the array.
        domain : str
            The domain of the array.
        var : str
            The name of the array.
        val : str
            The optional value of the array variable statement.
        output : bool
            Whether the array variable is an output array.
        comment : str
            A comment to attach to the variable statement.
        """
        val = dzn_value(val) if val is not None else None
        self._statements.append(ArrayVariable(indexset, domain, var, val, output,
                                              comment))
        if output or _var_type_p.match(domain) and val is None:
            self._free_vars.add(var)
        self._array_dims[var] = len(indexset.split(','))
        self._modified = True

    def _load_model(self):
        if not self.model:
            if self.mzn_file:
                with open(self.mzn_file) as f:
                    self.model = f.read()
            else:
                self.model = ''
        return self.model

    def _parse_model_stmts(self):
        if self._parsed:
            return
        model = self._load_model()
        model = _comm_p.sub('', model)
        stmts = _stmt_p.findall(model)
        for stmt in stmts:
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
                    self._array_dims[var] = dim
        self._parsed = True

    def dzn_output_stmt(self, output_vars=None, comment=None):
        """Sets the output statement to be a dzn representation of output_vars.

        If output_var is not provided (= None) then the free variables of the
        model are used i.e. those variables that are declared but not defined in
        the model (not depending on other variables).

        Parameters
        ----------
        output_vars : list of str
            The list of output variables.
        comment : str
            A comment to attach to the output statement.
        """

        # Look for free variables and array dimensions in the model statements
        self._parse_model_stmts()

        # Set output vars to the free variables if None provided
        if output_vars is None:
            output_vars = list(self._free_vars)

        if not output_vars:
            return

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

    def compile(self, output_file=None):
        """Compiles the model and writes it to file.

        The compiled model contains the content of the template (if provided)
        plus the added variables and constraints. The solve and output
        statements will be replaced if new ones are provided.

        Parameters
        ----------
        output_file : file-like
            The file where to write the compiled model.

        Returns
        -------
        str
            A string containing the generated model.
        """
        model = self._load_model()

        if self._modified:
            lines = ['\n\n\n%%% GENERATED BY PYMZN %%%\n\n']

            for stmt in self._statements:
                lines.append(stmt.compile())

            if self._solve_stmt:
                model = _solve_stmt_p.sub('', model)
                lines.append(self._solve_stmt.compile() + '\n')

            if self._output_stmt:
                model = _output_stmt_p.sub('', model)
                lines.append(self._output_stmt.compile() + '\n')

            model += '\n'.join(lines)

        if output_file:
            output_file.write(model)

        return model

