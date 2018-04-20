# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import absolute_import, division, print_function

import os
import sys

from setuptools import setup

if not (sys.version_info[:2] == (2, 7) or sys.version_info[:2] >= (3, 3)):
    sys.exit("conda is only meant for Python 2.7 or 3.3 and up.  "
             "current version: %d.%d" % sys.version_info[:2])


# When executing setup.py, we need to be able to import ourselves, this
# means that we need to add the src directory to the sys.path.
src_dir = here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, src_dir)
import conda._vendor.auxlib.packaging  # NOQA

long_description = """
.. image:: https://s3.amazonaws.com/conda-dev/conda_logo.svg
   :alt: Conda Logo

Conda is a cross-platform, language-agnostic binary package manager. It is the
package manager used by `Anaconda
<http://docs.continuum.io/anaconda/index.html>`_ installations, but it may be
used for other systems as well.  Conda makes environments first-class
citizens, making it easy to create independent environments even for C
libraries. Conda is written entirely in Python, and is BSD licensed open
source.

"""
install_requires = [
    "pycosat >=0.6.3",
    "requests >=2.12.4",
    "enum34 ; python_version<'3.4'",
    "futures ; python_version<'3.4'",
    "menuinst ; platform_system=='Windows'",
]

if os.getenv('CONDA_BUILD', None) == '1':
    install_requires.append("ruamel_yaml >=0.11.14")
else:
    install_requires.append("ruamel.yaml >=0.11.14")


def package_files(*root_directories):
    return [
        os.path.join('..', path, filename)
        for directory in root_directories
        for (path, directories, filenames) in os.walk(directory)
        for filename in filenames
    ]


setup(
    name=conda.__name__,
    version=conda.__version__,
    author=conda.__author__,
    author_email=conda.__email__,
    url=conda.__url__,
    license=conda.__license__,
    description=conda.__summary__,
    long_description=long_description,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    packages=conda._vendor.auxlib.packaging.find_packages(exclude=(
        "tests",
        "tests.*",
        "build",
        "utils",
        ".tox"
    )),
    package_data={
        '': package_files('conda/shell') + ['LICENSE'],
    },
    cmdclass={
        'build_py': conda._vendor.auxlib.packaging.BuildPyCommand,
        'sdist': conda._vendor.auxlib.packaging.SDistCommand,
    },
    entry_points={
        'console_scripts': [
            'conda=conda.cli.main_pip:main',
        ],
    },
    install_requires=install_requires,
    zip_safe=False,
)
