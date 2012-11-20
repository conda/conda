
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

# This is deprecated, do not use in new code
from envs import get_installed
