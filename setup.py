#!/usr/bin/env python
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import sys
import os

try:
    from setuptools import setup
    using_setuptools = True
except ImportError:
    from distutils.core import setup
    using_setuptools = False

add_activate = True

import versioneer


if sys.version_info[:2] < (2, 7):
    sys.exit("conda is only meant for Python 2.7, with experimental support "
             "for python 3.  current version: %d.%d" % sys.version_info[:2])

try:
    if os.environ['CONDA_DEFAULT_ENV']:
        # Try to prevent accidentally installing conda into a non-root conda environment
        sys.exit("You appear to be in a non-root conda environment. Conda is only "
            "supported in a non-root environment. Deactivate and try again. If believe "
            "this message is in error, run CONDA_DEFAULT_ENV='' python setup.py.")
except KeyError:
    pass

versioneer.versionfile_source = 'conda/_version.py'
versioneer.versionfile_build = 'conda/_version.py'
versioneer.tag_prefix = '' # tags are like 1.2.0
versioneer.parentdir_prefix = 'conda-' # dirname like 'myproject-1.2.0'

kwds = {'scripts': []}
if sys.platform == 'win32' and using_setuptools:
    kwds['entry_points'] = dict(console_scripts =
                                        ["conda = conda.cli.main:main"])
else:
    kwds['scripts'].append('bin/conda')

if add_activate:
    if sys.platform == 'win32':
        kwds['scripts'].extend(['bin/activate.bat', 'bin/deactivate.bat'])
    else:
        kwds['scripts'].extend(['bin/activate', 'bin/deactivate'])

setup(
    name = "conda",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author = "Continuum Analytics, Inc.",
    author_email = "ilan@continuum.io",
    url = "https://github.com/conda/conda",
    license = "BSD",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
    ],
    description = "package management tool",
    long_description = open('README.rst').read(),
    packages = ['conda', 'conda.cli', 'conda.progressbar'],
    install_requires = ['pycosat', 'pyyaml'],
    **kwds
)
