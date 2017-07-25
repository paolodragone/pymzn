# -*- coding: utf-8 -*-
u"""PyMzn can also be used to dynamically change a model during runtime. For
example, it can be useful to add constraints incrementally or change the solving
statement dynamically. To dynamically modify a model, you can use the class
``MiniZincModel``, providing a template model file as input which can then
be modified by adding variables and constraints, and by modifying the solve or
output statements. An instance of ``MiniZincModel`` can then be passed directly
to the ``minizinc`` function to be solved.
::

    model = pymzn.MiniZinModel('test.mzn')

    for i in range(10):
        model.constraint('arr_1[i] <= arr_2[i]')
        pymzn.minizinc(model)
"""

from __future__ import with_statement
from __future__ import absolute_import
import re
import os.path

from pymzn.dzn.marsh import stmt2dzn, val2dzn
from io import open


type_p = re.compile(u'\s*(?:int|float|set\s+of\s+[\s\w\.]+|array\[[\s\w\.]+\]\s*of\s*[\s\w\.]+)\s*')
var_type_p = re.compile(u'\s*.*?var.+\s*')
array_type_p = re.compile(u'\s*array\[([\s\w\.]+(?:\s*,\s*[\s\w\.]+)*)\]\s+of\s+(.+)\s*')
output_stmt_p = re.compile(u'\s*output\s*\[(.+?)\]\s*(?:;)?\s*')
solve_stmt_p = re.compile(u'\s*solve\s*([^;]+)\s*(?:;)?\s*')


class Statement(object):
    u"""A statement of a MiniZincModel.

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
    u"""A comment statement.

    Attributes
    ----------
    comment : str
        The comment string.
    """
    def __init__(self, comment):
        self.comment = comment
        stmt = u'% {}\n'.format(comment)
        super(Comment, self).__init__(stmt)


class Constraint(Statement):
    u"""A constraint statement.

    Attributes
    ----------
    constr : str
        The content of the constraint, i.e. only the actual constraint without
        the starting 'constraint' and the ending semicolon.
    """
    def __init__(self, constr, comment=None):
        self.constr = constr
        stmt = u'constraint {};'.format(constr)
        super(Constraint, self).__init__(stmt)


class Parameter(Statement):
    u"""A parameter statement.

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
    def __init__(self, *par, **_3to2kwargs):
        if 'assign' in _3to2kwargs: assign = _3to2kwargs['assign']; del _3to2kwargs['assign']
        else: assign = True
        name, par = par
        self.name = name
        self.type = None
        self.value = None
        self.assign = assign
        if isinstance(par, unicode):
            type_m = type_p.match(par)
            if type_m:
                self.type = par
        if not self.type:
            self.value = par
        if self.type:
            stmt = u'{}: {};'.format(self.type, self.name)
        else:
            stmt = stmt2dzn(self.name, self.value, assign=assign)
        super(Parameter, self).__init__(stmt)


class Variable(Statement):
    u"""A variable statement.

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
            if u'var' not in domain:
                vartype = u'array[{}] of var {}'.format(indexset, domain)
        elif u'var' not in vartype:
            vartype = u'var ' + vartype
        self.vartype = vartype

        stmt = u'{}: {}'.format(vartype, name)
        if output:
            if array_type_m:
                stmt += u' :: output_array([{}])'.format(indexset)
            else:
                stmt += u' :: output_var'
        if value:
            stmt += u' = {}'.format(value)
        stmt += u';'

        super(Variable, self).__init__(stmt)


class ArrayVariable(Variable):
    u"""An array variable statement.

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
        vartype = u'array[{}] of var {}'.format(indexset, domain)
        super(ArrayVariable, self).__init__(name, vartype, value, output)


class OutputStatement(Statement):
    u"""An output statement.

    Attributes
    ----------
    output : str
        The content of the output statement, i.e. only the actual output without
        the starting 'output', the square brackets and the ending semicolon.
    """
    def __init__(self, output):
        self.output = output
        if output:
            stmt = u'output [{}];'.format(output)
        else:
            stmt = u''
        super(OutputStatement, self).__init__(stmt)


class SolveStatement(Statement):
    u"""A solve statement.

    Attributes
    ----------
    solve : str
        The content of the solve statement, i.e. only the actual solve without
        the starting 'solve' and the ending semicolon.
    """

    def __init__(self, solve):
        self.solve = solve
        stmt = u'solve {};'.format(solve)
        super(SolveStatement, self).__init__(stmt)


class MiniZincModel(object):
    u"""Mutable class representing a MiniZinc model.

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
        self._modified = False

        self.mzn_file = None
        self.model = None
        if mzn and isinstance(mzn, unicode):
            if os.path.isfile(mzn):
                self.mzn_file = mzn
            else:
                self.model = mzn

    def comment(self, comment):
        u"""Add a comment to the model.

        Parameters
        ----------
        comment : str
            The comment string.
        """
        if not isinstance(comment, Comment):
            comment = Comment(comment)
        self._statements.append(comment)
        self._modified = True

    def parameter(self, *par, **_3to2kwargs):
        if 'assign' in _3to2kwargs: assign = _3to2kwargs['assign']; del _3to2kwargs['assign']
        else: assign = True
        u"""Adds a parameter to the model.

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
        u"""Add a list of parameters.

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
        u"""Adds a variable to the model.

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
        value = val2dzn(value) if value is not None else None
        array_type_m = array_type_p.match(vartype)
        if array_type_m:
            indexset = array_type_m.group(1)
            domain = array_type_m.group(2)
            dim = len(indexset.split(u','))
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
        u"""Adds an array variable to the model.

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
        value = val2dzn(value) if value is not None else None
        var = ArrayVariable(name, indexset, domain, value, output)
        self._statements.append(var)
        if output or var_type_p.match(domain) and value is None:
            self._free_vars.add(name)
        self._array_dims[var] = len(indexset.split(u','))
        self._modified = True

    def constraint(self, constr):
        u"""Adds a constraint to the current model.

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
        u"""Add a list of constraints.

        Parameters
        ----------
        constrs : list of str or Constraint
            A list of constraints.
        """
        for constr in constrs:
            self.constraint(constr)

    def solve(self, solve_stmt):
        u"""Updates the solve statement of the model.

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
        u"""Shorthand for solve('satisfy')"""
        self._solve_stmt = SolveStatement(u'satisfy')
        self._modified = True

    def maximize(self, expr):
        u"""Shorthand for solve('maximize ' + expr)"""
        self._solve_stmt = SolveStatement(u'maximize ' + expr)
        self._modified = True

    def minimize(self, expr):
        u"""Shorthand for solve('minimize ' + expr)"""
        self._solve_stmt = SolveStatement(u'minimize ' + expr)
        self._modified = True

    def output(self, output_stmt):
        u"""Updates the output statement of the model.

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
                self.model = u''
        return self.model

    def compile(self, output_file=None):
        u"""Compiles the model and writes it to file.

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
            lines = [u'\n\n\n%%% GENERATED BY PYMZN %%%\n\n']

            for stmt in self._statements:
                lines.append(unicode(stmt))

            if self._solve_stmt:
                model = solve_stmt_p.sub(u'', model)
                lines.append(unicode(self._solve_stmt) + u'\n')

            if self._output_stmt:
                model = output_stmt_p.sub(u'', model)
                lines.append(unicode(self._output_stmt) + u'\n')

            model += u'\n'.join(lines)

        if output_file:
            output_file.write(model)

        return model

