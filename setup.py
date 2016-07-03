import os
import codecs
import pymzn

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()

long_description = read('README.rst')

setup(
    name='pymzn',
    version=pymzn.__version__,
    url='https://github.com/paolodragone/PyMzn',
    license='MIT',
    author='Paolo Dragone',
    author_email='paolo.dragone@unitn.it',
    description='A Python3 wrapper for the MiniZinc tool pipeline.',
    long_description=long_description,
    packages=find_packages(exclude=['*.test_pymzn']),
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
