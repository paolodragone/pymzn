
import re

stmt_p = re.compile('(?:^|;)\s*([^;]+)')
comm_p = re.compile('%.*\n')
var_p = re.compile('\s*([^:]+?):\s*(\w+)\s*(?:=\s*(.+))?\s*')
type_p = re.compile('\s*(?:int|float|set\s+of\s+[\s\w\.]+|array\[[\s\w\.]+\]\s*of\s*[\s\w\.]+)\s*')
var_type_p = re.compile('\s*.*?var.+\s*')
array_type_p = re.compile('\s*array\[([\s\w\.]+(?:\s*,\s*[\s\w\.]+)*)\]\s+of\s+(.+)\s*')
output_stmt_p = re.compile('\s*output\s*\[(.+?)\]\s*(?:;)?\s*')
solve_stmt_p = re.compile('\s*solve\s*([^;]+)\s*(?:;)?\s*')
constraint_p = re.compile('\s*constraint\s*(.+)\s*')


def parse(model):
    model = comm_p.sub('', model)
    stmts = stmt_p.findall(model)
    parameters = []
    variables = []
    constraints = []
    solve = None
    output = None
    others = []
    for stmt in stmts:
        if not stmt.strip():
            continue
        var_m = var_p.match(stmt)
        if var_m:
            vartype = var_m.group(1)
            name = var_m.group(2)
            value = var_m.group(3)
            var_type_m = var_type_p.match(vartype)
            if not var_type_m:
                par = name, vartype, value
                parameters.append(par)
                continue
            var = name, vartype, value
            variables.append(var)
            continue
        constraint_m = constraint_p.match(stmt)
        if constraint_m:
            constraint = constraint_m.group(1)
            constraints.append(constraint)
            continue
        solve_stmt_m = solve_stmt_p.match(stmt)
        if solve_stmt_m:
            solve = solve_stmt_m.group(1)
            continue
        output_stmt_m = output_stmt_p.match(stmt)
        if output_stmt_m:
            output = output_stmt_m.group(1)
            continue
        others.append(stmt)
    return parameters, variables, constraints, solve, output, others
