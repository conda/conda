# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import

from conda._version import get_versions
__version__ = get_versions()['version']
del get_versions

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
