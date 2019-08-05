# -*- coding: utf-8 -*-
"""\
PyMzn supports templating as a form of dynamic modelling. PyMzn allows to embed
code from the `Jinja2 <http://jinja.pocoo.org/>`_ templating language within a
MiniZinc model to make a PyMzn template file (usually distinguished with the
``.pmzn`` extension). An example:

.. literalinclude:: ../../../../examples/templates/knapsack.pmzn
  :language: pymzn
  :caption: :download:`knapsack.pmzn <../../../../examples/templates/knapsack.pmzn>`
  :name: ex-knapsack-comp
  :linenos:

.. literalinclude:: ../../../../examples/templates/knapsack.dzn
  :language: minizinc
  :caption: :download:`knapsack.dzn <../../../../examples/templates/knapsack.dzn>`
  :name: ex-knapsack-comp-dzn
  :linenos:

The above MiniZinc model encodes a 0-1 knapsack problem with optional
compatibility constraint. By default the template engine argument
``with_compatibility`` is ``None``, so the constraint is not enabled. In this
case, the model can be solved as usual by running:

.. code-block:: python3

    pymzn.minizinc('knapsack.pmzn', 'knapsack.dzn')

which returns:

.. code-block:: python3

    [{'x': {2, 3, 5}}]

If we want to use the compatibility constraint, we define a compatibility
matrix e.g. in a dzn file:

.. literalinclude:: ../../../../examples/templates/compatibility.dzn
  :language: minizinc
  :caption: :download:`compatibility.dzn <../../../../examples/templates/compatibility.dzn>`
  :name: ex-knapsack-comp-dzn-comp
  :linenos:

Now it is possible to pass ``with_compatibility`` argument to ``pymzn.minizinc``
function, along with the dzn file with the compatibility matrix:

.. code-block:: python3

    pymzn.minizinc('knapsack.pmzn', 'knapsack.dzn', 'compatibility.dzn', args={'with_compatibility': True})

which yields:

.. code-block:: python3

    [{'x': {1, 5}}]

As mentioned, PyMzn employs Jinja2 under the hood, so anything you can do with
Jinja2 is also possible in PyMzn, including variables, control structures,
template inheritance, and filters. PyMzn implements few custom filters as well:

- ``int(value, factor=100)`` : discretizes the given input or array,
  pre-multiplying by the given factor. Usage:
  ``{{ float_value_or_array | int}}`` or ``{{ float_value_or_array | int(factor=1000) }}``
- ``dzn(value)`` : transform the input into its equivalent dzn string. Usage:
  ``{{ dzn_argument | dzn }}``

To provide a custom search path to the template engine you can use the
function ``add_path``:

.. code-block:: python3

    pymzn.templates.add_path('path/to/templates/directory/')

This ensures that the template engine will look for imported tempates into the
provided path as well.
"""

from .. import val2dzn, logger

from copy import deepcopy
from collections.abc import Iterable


__all__ = ['from_string', 'add_path', 'add_package']


def discretize(value, factor=100):
    """Discretize the given value, pre-multiplying by the given factor"""
    if not isinstance(value, Iterable):
        return int(value * factor)
    int_value = list(deepcopy(value))
    for i in range(len(int_value)):
        int_value[i] = int(int_value[i] * factor)
    return int_value

try:
    from jinja2 import (
        Environment, BaseLoader, PackageLoader, FileSystemLoader,
        TemplateNotFound
    )
    _has_jinja = True
except ImportError:
    _has_jinja = False

if _has_jinja:

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

_except_text = (
    '\nThe template engine is currently not available.\nTo use templates make '
    'sure Jinja2 is installed on your system.\nYou can install Jinja2 via pip:'
    '\n\n\tpip install Jinja2\n\nMore information at: '
    'http://jinja.pocoo.org/docs/intro/#installation'
)

def from_string(source, args=None):
    """Renders a template string"""
    if _has_jinja:
        logger.info('Preprocessing model with arguments: {}'.format(args))
        return _jenv.from_string(source).render(args or {})
    if args:
        raise RuntimeError(_except_text)
    return source

def add_package(package_name, package_path='templates', encoding='utf-8'):
    """Adds the given package to the template search routine"""
    if not _has_jinja:
        raise RuntimeError(_except_text)
    _jload.add_loader(PackageLoader(package_name, package_path, encoding))


def add_path(searchpath, encoding='utf-8', followlinks=False):
    """Adds the given path to the template search routine"""
    if not _has_jinja:
        raise RuntimeError(_except_text)
    _jload.add_loader(FileSystemLoader(searchpath, encoding, followlinks))

