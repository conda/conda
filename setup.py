# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import sys
if 'develop' in sys.argv:
    import setuptools

from distutils.core import setup
import versioneer


if sys.version[:3] != '2.7':
    raise Exception("conda is only meant for Python 2.7, current version: %s" %
                    sys.version[:3])

versioneer.versionfile_source = 'conda/_version.py'
versioneer.versionfile_build = 'conda/_version.py'
versioneer.tag_prefix = '' # tags are like 1.2.0
versioneer.parentdir_prefix = 'conda-' # dirname like 'myproject-1.2.0'

scripts = ['bin/conda']
if sys.platform != 'win32':
    scripts.extend(['bin/activate', 'bin/deactivate'])

setup(
    name = "conda",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author = "Continuum Analytics, Inc.",
    author_email = "ilan@continuum.io",
    license = "BSD",
    description = "package management tool",
    long_description = open('README.rst').read(),
    packages = ['conda', 'conda.cli', 'conda.builder', 'conda.progressbar'],
    scripts = scripts,
)
