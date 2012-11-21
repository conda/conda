# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

# This is deprecated, do not use in new code
from envs import get_installed
