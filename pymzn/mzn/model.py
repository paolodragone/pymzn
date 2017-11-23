# -*- coding: utf-8 -*-
"""PyMzn can also be used to dynamically change a model during runtime. For
example, it can be useful to add constraints incrementally or change the solving
statement dynamically. To dynamically modify a model, you can use the class
``MiniZincModel``, providing a template model file as input which can then
be modified by adding variables and constraints, and by modifying the solve or
output statements. An instance of ``MiniZincModel`` can then be passed directly
to the ``minizinc`` function to be solved.
::

    model = pymzn.MiniZinModel('test.mzn')
    solutions = []
    for i in range(10):
        # add a new constraint and solve again
        model.constraint('arr_1[{0}] <= arr_2[{0}]'.format(i))
        solution = pymzn.minizinc(model)
        solutions.append(solution)
"""

import re
import os.path

from .templates import from_string
from ..dzn.marsh import stmt2dzn, val2dzn

from copy import deepcopy

stmt_p = re.compile('(?:^|;)\s*([^;]+)')
stmts_p = re.compile('(?:^|;)([^;]+)')
block_comm_p = re.compile('/\*.*\*/', re.DOTALL)
line_comm_p = re.compile('%.*\n')
var_p = re.compile('\s*([\s\w,\.\(\)\[\]\{\}\+\-\*/]+?):\s*(\w+)\s*(?:=\s*(.+))?\s*', re.DOTALL)
type_p = re.compile('\s*(?:int|float|set\s+of\s+[\s\w\.]+|array\[[\s\w\.]+\]\s*of\s*[\s\w\.]+)\s*')
array_type_p = re.compile('\s*array\[([\s\w\.]+(?:\s*,\s*[\s\w\.]+)*)\]\s+of\s+(.+)\s*')
output_stmt_p = re.compile('\s*output\s*\[(.+?)\]\s*(?:;)?\s*')
solve_stmt_p = re.compile('\s*solve\s*([^;]+)\s*(?:;)?\s*')


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
            stmt = stmt2dzn(self.name, self.value, assign=assign)
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
        if output:
            stmt = 'output [{}];'.format(output)
        else:
            stmt = ''
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
    mzn : str or MiniZincModel
        A string with the content or the path to the template mzn file. If mzn
        is instead a MiniZincModel it is cloned.
    """
    def __init__(self, mzn=None):
        if mzn and isinstance(mzn, MiniZincModel):
            # if mzn is a MiniZincModel, clone it
            self.__dict__ = deepcopy(mzn.__dict__)
        else:
            self._statements = []
            self._solve_stmt = None
            self._output_stmt = None
            self._arrays = []
            self._modified = False
            self._output_vars = None

            self.mzn_file = None
            self.model = None
            if mzn and isinstance(mzn, str):
                if mzn.endswith('mzn'):
                    if os.path.isfile(mzn):
                        self.mzn_file = mzn
                    else:
                        raise ValueError('The provided file does not exsist.')
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
            Whether the variable is an output variable. This option is only used
            to force the compiled minizinc model to include the output_var or
            output_array annotation for this variable.
        """
        value = val2dzn(value) if value is not None else None
        array_type_m = array_type_p.match(vartype)
        if array_type_m:
            indexset = array_type_m.group(1)
            domain = array_type_m.group(2)
            dim = len(indexset.split(','))
            self._arrays.append((name, dim))
            var = ArrayVariable(name, indexset, domain, value, output)
        else:
            var = Variable(name, vartype, value, output)
        self._statements.append(var)
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
            Whether the array variable is an output array. This option is only
            used to force the compiled minizinc model to include the
            output_array annotation for this variable.
        """
        value = val2dzn(value) if value is not None else None
        var = ArrayVariable(name, indexset, domain, value, output)
        self._statements.append(var)
        self._arrays.append((var, len(indexset.split(','))))
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

    def _parse_arrays(self):
        model = self._load_model()
        model = block_comm_p.sub('', model)
        model = line_comm_p.sub('', model)
        stmts = stmt_p.findall(model)
        arrays = []
        for stmt in stmts:
            if not stmt.strip():
                continue
            var_m = var_p.match(stmt)
            if var_m and not ('function' in stmt or 'predicate' in stmt):
                vartype = var_m.group(1)
                name = var_m.group(2)
                array_type_m = array_type_p.match(vartype)
                if array_type_m:
                    dim = len(array_type_m.group(1).split(','))
                    arrays.append((name, dim))
        return arrays

    def dzn_output(self, output_vars):
        """Sets the output statement to be a dzn representation of output_vars.

        Parameters
        ----------
        output_vars : list of str
            The list of output variables.
        """
        if not output_vars:
            return
        self._output_vars = output_vars

    def _make_dzn_output(self):
        # Parse the model to look for array declarations
        arrays = self._parse_arrays() + self._arrays

        # Build the output statement from the output variables
        out_var = '"{0} = ", show({0}), ";\\n"'
        out_array = '"{0} = array{1}d(", {2}, ", ", show({0}), ");\\n"'
        out_list = []
        for var in self._output_vars:
            if var in arrays:
                name, dim = var
                if dim == 1:
                    show_idx_sets = 'show(index_set({}))'.format(var)
                else:
                    show_idx_sets = []
                    for d in range(1, dim + 1):
                        show_idx_sets.append('show(index_set_{}of{}'
                                             '({}))'.format(d, dim, name))
                    show_idx_sets = ', ", ", '.join(show_idx_sets)
                out_list.append(out_array.format(name, dim, show_idx_sets))
            else:
                out_list.append(out_var.format(var))
        self.output(', '.join(out_list))

    def _redefine_output_vars(self, model):
        model = block_comm_p.sub('', model)
        model = line_comm_p.sub('', model)
        stmts = stmt_p.findall(model)
        modified = []
        for stmt in stmts:
            var_m = var_p.match(stmt)
            if var_m and not ('function' in stmt or 'predicate' in stmt):
                name = var_m.group(2)
                if name in self._output_vars:
                    vartype = var_m.group(1)
                    value = var_m.group(3)
                    mod = [vartype, ': ', name]
                    array_type_m = array_type_p.match(vartype)
                    if array_type_m:
                        index_set = array_type_m.group(1)
                        mod.append(' :: output_array([{}])'.format(index_set))
                    else:
                        mod.append(' :: output_var')
                    if value:
                        mod += [' = ', value]
                    mod.append(';')
                    modified.append(''.join(mod))
                    continue
            modified.append(stmt + (';' if stmt.strip() else ''))
        return '\n'.join(modified)

    @staticmethod
    def _rewrap(s):
        S = {' ', '\t', '\n', '\r', '\f', '\v'}
        stmts = []
        for stmt in stmts_p.findall(s):
            spaces = 0
            while spaces < len(stmt) and stmt[spaces] in S:
                spaces += 1
            spaces -= stmt[0] == '\n'
            lines = []
            for line in stmt.splitlines():
                start = 0
                while start < len(line) and start < spaces and line[start] in S:
                    start += 1
                lines.append(line[start:])
            stmts.append('\n'.join(lines))
        return ';\n'.join(stmts)

    def compile(self, output_file=None, args=None, rewrap=False):
        """Compiles the model and writes it to file.

        The compiled model contains the content of the template (if provided)
        plus the added variables and constraints. The solve and output
        statements will be replaced if new ones are provided.

        Parameters
        ----------
        output_file : file-like
            The file where to write the compiled model.
        args : dict
            The argumets to pass to the template engine.
        rewrap : bool
            Whether to 'prettify' the model by adjusting the indentation of the
            statements. Use only if you want to actually look at the compiled
            model.

        Returns
        -------
        str
            A string containing the generated model.
        """
        model = self._load_model()
        model = from_string(model, args)

        if rewrap:
            model = self._rewrap(model)

        if self._output_vars is not None:
            self._make_dzn_output()
            model = self._redefine_output_vars(model)

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

