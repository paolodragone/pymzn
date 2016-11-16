#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.insert(0, os.path.abspath('../../'))

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'numpydoc'
]

autosummary_generate = True
numpydoc_show_class_members = False

templates_path = ['_templates']
exclude_patterns = []

source_suffix = '.rst'
master_doc = 'index'
html_theme = 'sphinx_rtd_theme'

language = None
today_fmt = '%B %d, %Y'
default_role = 'autolink'
pygments_style = 'sphinx'
todo_include_todos = False
htmlhelp_basename = 'pymzn'

project = 'PyMzn'
copyright = '2016, Paolo Dragone (MIT Licence)'
author = 'Paolo Dragone'

import pymzn
version = pymzn.__version__
release = pymzn.__version__

