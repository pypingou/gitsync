#!/usr/bin/env python

"""
Setup script
"""

import os
import re

from setuptools import setup


gitsyncfile = os.path.join(os.path.dirname(__file__), 'gitsync.py')
# Thanks to SQLAlchemy:
# https://github.com/zzzeek/sqlalchemy/blob/master/setup.py#L104
with open(gitsyncfile) as stream:
    __version__ = re.compile(
        r".*__version__ = '(.*?)'", re.S
    ).match(stream.read()).group(1)


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


setup(
    name='gitsync',
    description='Keep your git folder always in sync with its server',
    version=__version__,
    author='Pierre-Yves Chibon',
    author_email='pingou@pingoured.fr',
    url='https://github.com/pypingou/gitsync',
    download_url='https://pypi.python.org/pypi/gitsync',
    license='GPLv3+',
    py_modules=['gitsync'],
    install_requires=get_requires(),
    entry_points={
        'console_scripts': [
            "gitsync-cli=gitsync:main",
        ]
    },
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: System :: Archiving',
        'Topic :: Utilities',
    ]
)
