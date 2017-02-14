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


# pip/wheel no longer displaying this message is unfortunate
# https://github.com/pypa/pip/issues/2933
print("""
WARNING: Your current install method for conda only supports conda
as a python library.  You are not installing a conda executable command
or activate/deactivate commands.  If your intention is to install conda
as a standalone application, currently supported install methods include
the Anaconda installer and the miniconda installer.  If you'd still like
for setup.py to create entry points for you, use `utils/setup-testing.py`.
""", file=sys.stderr)


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


### Installation

**WARNING:** Using ``pip install conda`` or ``easy_install conda`` will not
give you conda as a standalone application.  Currently supported install
methods include the Anaconda installer and the miniconda installer.  You
can download the miniconda installer from https://conda.io/miniconda.html.

"""

install_requires = [
    'pycosat >=0.6.1',
    'requests >=2.12.4',
    'ruamel.yaml >=0.11.14'
]


if sys.version_info < (3, 4):
    install_requires.append('enum34')


if sys.platform == "win32":
    install_requires.append('menuinst')


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
    packages=conda._vendor.auxlib.packaging.find_packages(exclude=("tests",
                                                                   "tests.*",
                                                                   "build",
                                                                   "utils",
                                                                   ".tox")),
    cmdclass={
        'build_py': conda._vendor.auxlib.packaging.BuildPyCommand,
        'sdist': conda._vendor.auxlib.packaging.SDistCommand,
    },
    entry_points={
        'console_scripts': [
            'conda=conda.cli.pip_warning:main',
        ],
    },
    install_requires=install_requires,
    zip_safe=False,
)
