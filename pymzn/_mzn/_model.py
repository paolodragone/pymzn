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

from pymzn._utils import get_logger
from pymzn._dzn._marsh import dzn_statement, dzn_value
from pymzn._mzn._parse import *


class Statement(object):
    """A statement of a MiniZincModel.

    Attributes
    ----------
    stmt : str
        The statement string.
    """
    def __init__(self, stmt):
        self.stmt = stmt

    def __str__(self):
        return self.stmt


class Comment(Statement):
    """A comment statement.

    Attributes
    ----------
    comment : str
        The comment string.
    """
    def __init__(self, comment):
        self.comment = comment
        stmt = '% {}\n'.format(comment)
        super().__init__(stmt)


class Constraint(Statement):
    """A constraint statement.

    Attributes
    ----------
    constr : str
        The content of the constraint, i.e. only the actual constraint without
        the starting 'constraint' and the ending semicolon.
    """
    def __init__(self, constr, comment=None):
        self.constr = constr
        stmt = 'constraint {};'.format(constr)
        super().__init__(stmt)


class Parameter(Statement):
    """A parameter statement.

    Attributes
    ----------
    par : (str, str) or (str, obj)
        Either a (name, type) pair or a (name, value) pair. In the latter case
        the type is automatically inferred from the value.
    assign : bool
        If True the parameter value will be assigned directly into the model,
        otherwise it will only be declared in the model and then it will have to
        be assigned in the data.
    """
    def __init__(self, *par, assign=True):
        name, par = par
        self.name = name
        self.type = None
        self.value = None
        self.assign = assign
        if isinstance(par, str):
            type_m = type_p.match(par)
            if type_m:
                self.type = par
        if not self.type:
            self.value = par
        if self.type:
            stmt = '{}: {};'.format(self.type, self.name)
        else:
            stmt = dzn_statement(self.name, self.value, assign=assign)
        super().__init__(stmt)


class Variable(Statement):
    """A variable statement.

    Attributes
    ----------
    name : str
        The name of the variable.
    vartype : str
        The type of the variable.
    value : str
        The optional value of the variable statement.
    output : bool
        Whether the variable is an output variable.
    """
    def __init__(self, name, vartype, value=None, output=False):
        self.name = name
        self.value = value
        self.output = output

        array_type_m = array_type_p.match(vartype)
        if array_type_m:
            indexset = array_type_m.group(1)
            domain = array_type_m.group(2)
            if 'var' not in domain:
                vartype = 'array[{}] of var {}'.format(indexset, domain)
        elif 'var' not in vartype:
            vartype = 'var ' + vartype
        self.vartype = vartype

        stmt = '{}: {}'.format(vartype, name)
        if output:
            if array_type_m:
                stmt += ' :: output_array([{}])'.format(indexset)
            else:
                stmt += ' :: output_var'
        if value:
            stmt += ' = {}'.format(value)
        stmt += ';'

        super().__init__(stmt)


class ArrayVariable(Variable):
    """An array variable statement.

    Attributes
    ----------
    name : str
        The name of the variable.
    indexset : str
        The indexset of the array.
    domain : str
        The domain of the array.
    value : str
        The optional value of the variable statement.
    output : bool
        Whether the array variable is an output array.
    """
    def __init__(self, name, indexset, domain, value=None, output=False):
        self.indexset = indexset
        self.domain = domain
        vartype = 'array[{}] of var {}'.format(indexset, domain)
        super().__init__(name, vartype, value, output)


class OutputStatement(Statement):
    """An output statement.

    Attributes
    ----------
    output : str
        The content of the output statement, i.e. only the actual output without
        the starting 'output', the square brackets and the ending semicolon.
    """
    def __init__(self, output):
        self.output = output
        stmt = 'output [{}];'.format(output)
        super().__init__(stmt)


class SolveStatement(Statement):
    """A solve statement.

    Attributes
    ----------
    solve : str
        The content of the solve statement, i.e. only the actual solve without
        the starting 'solve' and the ending semicolon.
    """

    def __init__(self, solve):
        self.solve = solve
        stmt = 'solve {};'.format(solve)
        super().__init__(stmt)


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

        self.mzn_file = None
        self.model = None
        if mzn and isinstance(mzn, str):
            if os.path.isfile(mzn):
                self.mzn_file = mzn
            else:
                self.model = mzn

    def comment(self, comment):
        """Add a comment to the model.

        Parameters
        ----------
        comment : str
            The comment string.
        """
        if not isinstance(comment, Comment):
            comment = Comment(comment)
        self._statements.append(comment)
        self._modified = True

    def parameter(self, *par, assign=True):
        """Adds a parameter to the model.

        Parameters
        ----------
        par : Parameter or (str, str) or (str, obj)
            Either a Parameter, a (name, type) pair or a (name, value) pair. In
            the latter case, the type is inferred automatically from the value.
        assign : bool
            If True the parameter value will be assigned directly into the
            model, otherwise it will only be declared in the model and then it
            will have to be assigned in the data.
        """
        if isinstance(par[0], Parameter):
            par = par[0]
        else:
            par = Parameter(*par, assign=assign)
        self._statements.append(par)
        self._modified = True

    def parameters(self, pars, assign=True):
        """Add a list of parameters.

        Parameters
        ----------
        pars : list of (name, val) or Parameter
            The list of parameters to add to the model.
        assign : bool
            If True the parameters value will be assigned directly into the
            model, otherwise they will only be declared in the model and then
            they will have to be assigned in the data.
        """
        for par in pars:
            self.parameter(*par, assign=assign)
        self._modified = True

    def variable(self, name, vartype, value=None, output=False):
        """Adds a variable to the model.

        Parameters
        ----------
        name : str
            The name of the variable.
        vartype : str
            The type of the variable.
        value : str
            The optional value of the variable statement.
        output : bool
            Whether the variable is an output variable.
        """
        value = dzn_value(value) if value is not None else None
        array_type_m = array_type_p.match(vartype)
        if array_type_m:
            indexset = array_type_m.group(1)
            domain = array_type_m.group(2)
            dim = len(indexset.split(','))
            self._array_dims[name] = dim
            var = ArrayVariable(name, indexset, domain, value, output)
        else:
            var = Variable(name, vartype, value, output)
        self._statements.append(var)

        var_type_m = var_type_p.match(vartype)
        if output or var_type_m and value is None:
            self._free_vars.add(name)
        self._modified = True

    def array_variable(self, name, indexset, domain, value=None, output=False):
        """Adds an array variable to the model.

        Parameters
        ----------
        name : str
            The name of the array.
        indexset : str
            The indexset of the array.
        domain : str
            The domain of the array.
        value : str
            The optional value of the array variable statement.
        output : bool
            Whether the array variable is an output array.
        """
        value = dzn_value(value) if value is not None else None
        var = ArrayVariable(name, indexset, domain, value, output)
        self._statements.append(var)
        if output or var_type_p.match(domain) and value is None:
            self._free_vars.add(name)
        self._array_dims[var] = len(indexset.split(','))
        self._modified = True

    def constraint(self, constr):
        """Adds a constraint to the current model.

        Parameters
        ----------
        constr : str or Constraint
            As a string, the content of the constraint, i.e. only the actual
            constraint without the starting 'constraint' and the ending
            semicolon.
        """
        if not isinstance(constr, Constraint):
            constr = Constraint(constr)
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

    def solve(self, solve_stmt):
        """Updates the solve statement of the model.

        Parameters
        ----------
        solve_stmt : str
            The content of the solve statement, i.e. only the actual solve
            without the starting 'solve' and the ending semicolon.
        """
        if not isinstance(solve_stmt, SolveStatement):
            solve_stmt = SolveStatement(solve_stmt)
        self._solve_stmt = solve_stmt
        self._modified = True

    def satisfy(self):
        """Shorthand for solve('satisfy')"""
        self._solve_stmt = SolveStatement('satisfy')
        self._modified = True

    def maximize(self, expr):
        """Shorthand for solve('maximize ' + expr)"""
        self._solve_stmt = SolveStatement('maximize ' + expr)
        self._modified = True

    def minimize(self, expr):
        """Shorthand for solve('minimize ' + expr)"""
        self._solve_stmt = SolveStatement('minimize ' + expr)
        self._modified = True

    def output(self, output_stmt):
        """Updates the output statement of the model.

        Parameters
        ----------
        solve_stmt : str
            The content of the output statement, i.e. only the actual output
            without the starting 'output', the square brackets and the ending
            semicolon.
        """
        if not isinstance(output_stmt, OutputStatement):
            output_stmt = OutputStatement(output_stmt)
        self._output_stmt = output_stmt
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
        _, variables, *_ = parse(model)
        for var in variables:
            name, vartype, value = var
            if var_type_p.match(vartype) and value is None:
                self._free_vars.add(name)
            array_type_m = array_type_p.match(vartype)
            if array_type_m:
                dim = len(array_type_m.group(1).split(','))
                self._array_dims[name] = dim
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
        self.output(out_list)

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
                lines.append(str(stmt))

            if self._solve_stmt:
                model = solve_stmt_p.sub('', model)
                lines.append(str(self._solve_stmt) + '\n')

            if self._output_stmt:
                model = output_stmt_p.sub('', model)
                lines.append(str(self._output_stmt) + '\n')

            model += '\n'.join(lines)

        if output_file:
            output_file.write(model)

        return model

