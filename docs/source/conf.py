# -*- coding: utf-8 -*-

import os
import re
import sys
import codecs

sys.path.insert(0, os.path.abspath('../../'))
here = os.path.abspath(os.path.dirname(__file__))

def find_version(*parts):
    # Open in Latin-1 so that we avoid encoding errors.
    # Use codecs.open for Python 2 compatibility
    with codecs.open(os.path.join(here, *parts), 'r', 'latin1') as f:
        version_file = f.read()

    # The version line must have the form
    # __version__ = 'ver'
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

project = 'PyMzn'
copyright = '2016, Paolo Dragone (MIT License)'
author = 'Paolo Dragone'

version = find_version('..', '..', 'pymzn', '__init__.py')
release = find_version('..', '..', 'pymzn', '__init__.py')

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon'
]

autosummary_generate = True

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

language = None

exclude_patterns = []

pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
# html_theme_options = {}
html_static_path = ['_static']
html_copy_source = False

htmlhelp_basename = 'pymzn'

latex_elements = {
}

latex_documents = [
    (master_doc, 'pymzn.tex', 'PyMzn Documentation', 'Paolo Dragone', 'manual'),
]

