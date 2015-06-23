from os.path import basename
import conda.config as config
from conda.cli import common


def current_env():
    """Retrieves dictionary with current environment's name and prefix"""
    if config.default_prefix == config.root_dir:
        name = config.root_env_name
    else:
        name = basename(config.default_prefix)
    return {'name': name, 'prefix': config.default_prefix}
