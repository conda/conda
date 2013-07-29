# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import sys
if 'develop' in sys.argv:
    import setuptools

from distutils.core import setup
import versioneer


if sys.version_info[:2] < (2, 7):
    sys.exit("conda is only meant for Python 2.7, with experimental support "
             "for python 3.  current version: %d.%d" % sys.version_info[:2])

versioneer.versionfile_source = 'conda/_version.py'
versioneer.versionfile_build = 'conda/_version.py'
versioneer.tag_prefix = '' # tags are like 1.2.0
versioneer.parentdir_prefix = 'conda-' # dirname like 'myproject-1.2.0'

scripts = ['bin/conda']
if sys.platform == 'win32':
    pass #scripts.extend(['bin/activate.bat'])
else:
    scripts.extend(['bin/activate', 'bin/deactivate'])

setup(
    name = "conda",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author = "Continuum Analytics, Inc.",
    author_email = "ilan@continuum.io",
    url = "https://github.com/ContinuumIO/conda",
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
    packages = ['conda', 'conda.cli', 'conda.builder', 'conda.progressbar'],
    scripts = scripts,
)
