#!/usr/bin/env python
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import versioneer


if sys.version_info[:2] < (2, 7):
    sys.exit("conda is only meant for Python 2.7, with experimental support "
             "for python 3.  current version: %d.%d" % sys.version_info[:2])

versioneer.versionfile_source = 'conda_env/_version.py'
versioneer.versionfile_build = 'conda_env/_version.py'
versioneer.tag_prefix = ''
versioneer.parentdir_prefix = 'conda-env-'

setup(
    name="conda-env",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="Continuum Analytics, Inc.",
    author_email="travis.swicegood@continuum.io",
    url="https://github.com/tswicegood/conda-build",
    license="BSD",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
    ],
    description="tools for interacting with conda environments",
    long_description=open('README.rst').read(),
    packages=['conda_env'],
    scripts=[
        'bin/conda-env',
    ],
    entry_points={
        'conda.env.installers': [
            'conda = conda_env.installers.conda',
            'pip = conda_env.installers.pip',
        ],
    },
    install_requires=['conda'],
    package_data={},
)
