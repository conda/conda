import sys
from distutils.core import setup


if sys.version[:3] != '2.7':
    raise Exception("conda is only meant for Python 2.7, current version: %s" %
                    sys.version[:3])


setup(
    name = "conda",
    version = '1.1.0',
    author = "Continuum Analytics, Inc.",
    author_email = "ilan@continuum.io",
    description = "Conda tool",
    packages = ['conda', 'conda.cli', 'conda.progressbar'],
    scripts = ['bin/conda'],
)
