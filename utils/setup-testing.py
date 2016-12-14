# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
if 'develop' in sys.argv:
    from setuptools import setup
else:
    from distutils.core import setup

if not (sys.version_info[:2] == (2, 7) or sys.version_info[:2] >= (3, 3)):
    sys.exit("conda is only meant for Python 2.7 or 3.3 and up.  "
             "current version: %d.%d" % sys.version_info[:2])

# When executing setup.py, we need to be able to import ourselves, this
# means that we need to add the src directory to the sys.path.
here = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(here, "..")
sys.path.insert(0, src_dir)

import conda  # NOQA
from conda._vendor.auxlib import packaging  # NOQA

with open(os.path.join(src_dir, "README.rst")) as f:
    long_description = f.read()

scripts = ['shell/activate',
           'shell/deactivate',
           ]
if sys.platform == 'win32':
    # Powershell scripts should go here
    scripts.extend(['shell/activate.bat',
                    'shell/deactivate.bat'])

install_requires = [
    'pycosat >=0.6.1',
    'requests >=2.5.3',
]

if sys.version_info < (3, 4):
    install_requires.append('enum34')


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
    ],
    packages=packaging.find_packages(exclude=("tests",
                                              "tests.*",
                                              "build",
                                              "utils",
                                              ".tox")),
    cmdclass={
        'build_py': packaging.BuildPyCommand,
        'sdist': packaging.SDistCommand,
    },
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            "conda = conda.cli:main",
            "conda-env = conda_env.cli.main:main"
        ],
    },
    scripts=scripts,
    zip_safe=False,
)
