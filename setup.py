# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
import os
import sys
from textwrap import dedent

if not (sys.version_info[:2] == (2, 7) or sys.version_info[:2] >= (3, 3)):
    sys.exit(dedent("""\
        conda is only meant for Python 2.7 or 3.3 and up.
        current version: {}.{}""").format(*sys.version_info[:2]))

if os.environ.get('CONDA_DEFAULT_ENV'):
    # Try to prevent accidentally installing conda into a non-root conda environment
    sys.exit(dedent("""\
        You appear to be in a non-root conda environment. Conda is only supported in
        the root environment. Deactivate and try again.  If you believe this message
        is in error, run CONDA_DEFAULT_ENV='' python setup.py."""))

# When executing the setup.py, we need to be able to import ourselves, this
# means that we need to add the src directory to the sys.path.
here = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(here, "conda")
sys.path.insert(0, src_dir)

import conda  # NOQA
from conda._vendor.auxlib import packaging  # NOQA
if packaging.is_develop:
    from setuptools import setup
else:
    from distutils.core import setup

with open(os.path.join(here, "README.rst")) as f:
    long_description = f.read()

scripts = [
    'shell/activate',
    'shell/activate.sh',
    'shell/activate.csh',
    'shell/deactivate',
    'shell/deactivate.sh',
    'shell/deactivate.csh',
    'shell/whichshell_args.bash',
    'shell/whichshell_ps.bash',
    'shell/whichshell.awk',
    'shell/envvar_cleanup.bash',
]
if sys.platform == 'win32':
    # Powershell scripts should go here
    scripts += [
        'shell/activate.bat',
        'shell/deactivate.bat',
        'shell/envvar_cleanup.bat',
    ]

install_requires = [
    'pycosat >=0.6.1',
    'requests >=2.5.3',
]

if sys.version_info < (3, 4):
    install_requires.append('enum34')

cmdclass = {
    'build_py': packaging.BuildPyCommand,
    'sdist': packaging.SDistCommand,
}
if packaging.is_develop:
    cmdclass['develop'] = packaging.DevelopCommand
else:
    cmdclass['install_scripts'] = packaging.InstallScriptsCommand

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
    cmdclass=cmdclass,
    install_requires=[],
    entry_points={
        'console_scripts': [
            "conda = conda.cli.main:main",
            "conda-env = conda_env.cli.main:main"
        ],
    },
    scripts=scripts,
    zip_safe=False,
)
