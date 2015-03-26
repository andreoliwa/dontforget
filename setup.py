#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Setup script."""
from __future__ import absolute_import, print_function

import io
import re
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

try:
    from setuptools import find_packages, setup, Command
except ImportError:
    from distutils.core import find_packages, setup, Command


def requirements(extra_suffixes=None):
    """Return all lines from requirements.txt as a list.

    :param extra_suffixes: Extra file suffixes to add to the list.
    E.g.: a '_dev' suffix will all all lines from 'requirements_dev.txt' to the return list.
    :return:

    :type extra_suffixes: list
    """
    suffixes = ['']
    if extra_suffixes:
        suffixes.extend(extra_suffixes)

    all_lines = []
    for suffix in suffixes:
        try:
            with open('requirements{}.txt'.format(suffix)) as handle:
                text = handle.read()
                all_lines.extend(text.split('\n'))
        except FileNotFoundError:
            pass
    return [line for line in all_lines if '=' in line]


def read(*names, **kwargs):
    """Read files into a string.

    :param names: Names of the files.
    :param kwargs: Optional keyword arguments.
    :return:
    """
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


class PyTest(Command):

    """Setup command to invoke pytest."""

    user_options = []

    def initialize_options(self):
        """Initialize pytest options."""
        pass

    def finalize_options(self):
        """Finalize pytest options."""
        pass

    def run(self):
        """Call pytest script to run tests."""
        import subprocess
        import sys

        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)


setup(
    name='dontforget',
    version='0.1.0',
    license='BSD',
    description='A to-do list with recurring dates and reminders,'
                ' so you never again will forget to do something important',
    long_description='%s\n%s' % (read('README.rst'), re.sub(':obj:`~?(.*?)`', r'``\1``', read('CHANGELOG.rst'))),
    author='Wagner Augusto Andreoli',
    author_email='wagnerandreoli@gmail.com',
    url='https://github.com/wagnerandreoli/dontforget',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Topic :: Utilities',
    ],
    cmdclass={'test': PyTest},
    test_suite='tests',
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    install_requires=requirements(),
    tests_require=requirements(['_dev']),
    extras_require={
        # eg: 'rst': ['docutils>=0.11'],
    },
    entry_points={
        'console_scripts': [
            'dontforget = dontforget.__main__:main'
        ]
    },
)
