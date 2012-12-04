# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import versioneer


if sys.version[:3] != '2.7':
    raise Exception("conda is only meant for Python 2.7, current version: %s" %
                    sys.version[:3])

versioneer.versionfile_source = 'conda/_version.py'
versioneer.versionfile_build = 'conda/_version.py'
versioneer.tag_prefix = '' # tags are like 1.2.0
versioneer.parentdir_prefix = 'conda-' # dirname like 'myproject-1.2.0'

setup(
    name = "conda",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author = "Continuum Analytics, Inc.",
    author_email = "ilan@continuum.io",
    description = "Conda tool",
    packages = ['conda', 'conda.cli', 'conda.builder', 'conda.progressbar'],
    scripts = ['bin/conda'],
)
