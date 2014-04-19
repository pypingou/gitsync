#!/usr/bin/env python

"""
Setup script
"""

from gitsync import __version__
from setuptools import setup


def get_requires():
    ''' Reads the requirements.txt and return its content in a list. '''
    stream = open('requirements.txt')
    content = stream.readlines()
    stream.close()

    deps = []
    for row in content:
        if row.startswith('#'):
            continue
        else:
            deps.append(row.strip())

    return deps

requires = get_requires()

setup(
    name='gitsync',
    description='Keep your git folder always in sync with its server',
    version=__version__,
    author='Pierre-Yves Chibon',
    author_email='pingou@pingoured.fr',
    url='https://github.com/pypingou/gitsync',
    download_url = 'https://pypi.python.org/pypi/gitsync',
    py_modules=['gitsync'],
    install_requires=requires,
    entry_points={
        'console_scripts': [
            "gitsync-cli=gitsync:main",
        ]
    },
)
