from setuptools import setup, find_packages

import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()

long_description = read('README.rst')

setup(
    name='pymzn',
    version='0.9.2',
    url='https://github.com/paolodragone/PyMzn',
    license='MIT',
    author='Paolo Dragone',
    author_email='paolo.dragone@unitn.it',
    description='A Python3 wrapper for the MiniZinc tool pipeline.',
    long_description=long_description,
    packages=find_packages(exclude=['*.tests']),
    platforms='any',
    classifiers=[
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules']
)
