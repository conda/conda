# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
import os
import sys
if 'develop' in sys.argv:
    from setuptools import setup
else:
    from distutils.core import setup

if not (sys.version_info[:2] == (2, 7) or sys.version_info[:2] >= (3, 3)):
    sys.exit("conda is only meant for Python 2.7 or 3.3 and up.  "
             "current version: %d.%d" % sys.version_info[:2])

if os.environ.get('CONDA_DEFAULT_ENV'):
    # Try to prevent accidentally installing conda into a non-root conda environment
    sys.exit("""
You appear to be in a non-root conda environment. Conda is only supported in
the root environment. Deactivate and try again.  If you believe this message
is in error, run CONDA_DEFAULT_ENV='' python setup.py.
""")

# When executing the setup.py, we need to be able to import ourselves, this
# means that we need to add the src directory to the sys.path.
here = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.join(here, "conda")
sys.path.insert(0, src_dir)

import auxlib  # noqa -- build-time dependency only
import conda  # NOQA


with open(os.path.join(here, "README.rst")) as f:
    long_description = f.read()

scripts = ['bin/activate',
           'bin/deactivate', ]
if sys.platform == 'win32':
    # Powershell scripts should go here
    scripts.extend(['bin/activate.bat',
                    'bin/deactivate.bat'])

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
    packages=[
        'conda',
        'conda.cli',
        'conda.progressbar'
    ],
    cmdclass={
        'build_py': auxlib.BuildPyCommand,
        'sdist': auxlib.SDistCommand,
    },
    install_requires=[
        'psutil',
        'pycosat >=0.6.1',
        'pyyaml',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            "conda = conda.cli.main:main"
        ],
    },
    scripts=scripts,
    zip_safe=False,
)
