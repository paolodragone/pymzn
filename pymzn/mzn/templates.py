
from copy import deepcopy
from collections.abc import Iterable
from pymzn.dzn.marsh import val2dzn
from jinja2 import (
    Environment, Template, BaseLoader, PackageLoader, FileSystemLoader,
    TemplateNotFound
)


def discretize(value, factor=100):
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
    return _jenv.from_string(source).render(args or {})


def add_package(package_name, package_path='templates', encoding='utf-8'):
    _jload.add_loader(PackageLoader(package_name, package_path, encoding))


def add_path(searchpath, encoding='utf-8', followlinks=False):
    _jload.add_loader(FileSystemLoader(searchpath, encoding, followlinks))

