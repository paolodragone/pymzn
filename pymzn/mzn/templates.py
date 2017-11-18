# -*- coding: utf-8 -*-
"""Handles MiniZinc template files.

PyMzn supports templating as a form of dynamic modelling. PyMzn allows to embed
code from the `Jinja2 <http://jinja.pocoo.org/>`_ templating language within a
MiniZinc model to make a PyMzn template file (usually distinguished with the
`pmzn` extension). An example::

    %% knapsack.pmzn %%
    int: n;                     % number of objects
    set of int: OBJ = 1..n;
    int: capacity;              % the capacity of the knapsack
    array[OBJ] of int: size;    % the size of each object=

    var set of OBJ: x;
    constraint sum(i in x)(size[i]) <= capacity;

    {% if objective == 'profit' %}
        array[OBJ] of int: profit;  % the profit of each object
        solve maximize sum(i in x)(profit[i]);
    {% elif objective == 'cost' %}
        array[OBJ] of int: cost;    % the cost of each object
        solve minimize sum(i in x)(cost[i]);
    {% else %}
        solve satisfy;
    {% endif%}

    %% knapsack.dzn %%
    n = 5;
    size = [14, 4, 10, 6, 9];
    capacity = 20;

Now it is possible to pass `objective` as a member of `args` in the
`pymzn.minizinc` function::

    pymzn.minizinc('knapsack.pmzn', data={'cost': [10, 3, 9, 4, 8]}, args={'objective': 'cost'})

The compiled model that will be solved looks like this::

    %% knapsack.mzn %%
    int: n;                     % number of objects
    set of int: OBJ = 1..n;
    int: capacity;              % the capacity of the knapsack
    array[OBJ] of int: size;    % the size of each object=

    var set of OBJ: x;
    constraint sum(i in x)(size[i]) <= capacity;

    array[OBJ] of int: cost;    % the cost of each object
    solve minimize sum(i in x)(cost[i]);

Notice that now the model expects a `cost` array as dzn input data, so we passed
it with the `data` argument as usual.

As mentioned, PyMzn employs Jinja2 under the hood, so anything you can do with
Jinja2 is also possible in PyMzn, including variables, control structured,
template inheritance, and filters. PyMzn implements few custom filters as well:

- `int(value, factor=100)` : discretizes the given input or array,
  pre-multiplying by the given factor.
- `dzn(value)` : transform the input into its equivalent dzn string.
"""

from copy import deepcopy
from collections.abc import Iterable
from pymzn.dzn.marsh import val2dzn
from jinja2 import (
    Environment, Template, BaseLoader, PackageLoader, FileSystemLoader,
    TemplateNotFound
)


def discretize(value, factor=100):
    """Discretize the given value, pre-multiplying by the given factor"""
    if not isinstance(value, Iterable):
        return int(value * factor)
    int_value = list(deepcopy(value))
    for i in range(len(int_value)):
        int_value[i] = int(int_value[i] * factor)
    return int_value


class MultiLoader(BaseLoader):

    def __init__(self):
        self._loaders = []

    def add_loader(self, loader):
        self._loaders.append(loader)

    def get_source(self, environment, template):
        for loader in self._loaders:
            try:
                return loader.get_source(environment, template)
            except TemplateNotFound:
                pass
        raise TemplateNotFound(template)

    def list_templates(self):
        seen = set()
        templates = []
        for loader in self._loaders:
            for tmpl in loader.list_templates():
                if tmpl not in seen:
                    templates.append(tmpl)
                    seen.add(tmpl)
        return templates


_jload = MultiLoader()
_jenv = Environment(trim_blocks=True, lstrip_blocks=True, loader=_jload)
_jenv.filters['dzn'] = val2dzn
_jenv.filters['int'] = discretize


def from_string(source, args=None):
    """Renders a template string"""
    return _jenv.from_string(source).render(args or {})


def add_package(package_name, package_path='templates', encoding='utf-8'):
    """Adds the given package to the template search routine"""
    _jload.add_loader(PackageLoader(package_name, package_path, encoding))


def add_path(searchpath, encoding='utf-8', followlinks=False):
    """Adds the given path to the template search routine"""
    _jload.add_loader(FileSystemLoader(searchpath, encoding, followlinks))

