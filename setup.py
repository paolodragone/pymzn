from __future__ import with_statement
from __future__ import absolute_import
import re
import os
import codecs

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))


def find_version(*parts):
    # Open in Latin-1 so that we avoid encoding errors.
    # Use codecs.open for Python 2 compatibility
    with codecs.open(os.path.join(here, *parts), u'r', u'latin1') as f:
        version_file = f.read()

    # The version line must have the form
    # __version__ = 'ver'
    version_match = re.search(ur"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError(u"Unable to find version string.")


def read(*parts):
    with codecs.open(os.path.join(here, *parts), encoding=u'utf-8') as f:
        return f.read()


setup(
    name = u'pymzn',
    version = find_version(u'pymzn', u'__init__.py'),
    url = u'https://github.com/paolodragone/pymzn',
    license = u'MIT',
    author = u'Paolo Dragone',
    author_email = u'paolo.dragone@unitn.it',
    description = u'A Python wrapper for the MiniZinc tool pipeline.',
    long_description = read(u'README.rst'),
    packages = find_packages(exclude=[u'*tests*']),
    test_suite = u"pymzn.tests",
    install_requires = [
        u'appdirs',
        u'pyyaml'
    ],
    platforms = u'any',
    classifiers = [
        u'Programming Language :: Python',
        u'Programming Language :: Python :: 2',
        u'Programming Language :: Python :: 2.7',
        u'Programming Language :: Python :: 3',
        u'Programming Language :: Python :: 3.5',
        u'Development Status :: 4 - Beta',
        u'Natural Language :: English',
        u'Environment :: Console',
        u'Intended Audience :: Developers',
        u'License :: OSI Approved :: MIT License',
        u'Operating System :: OS Independent',
        u'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    entry_points = {
        u'console_scripts': [
            u'pymzn=pymzn:main'
        ]
    }
)
