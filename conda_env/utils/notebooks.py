import json
from os.path import basename
import conda.config as config
from conda.cli import common
from ..exceptions import EnvironmentAlreadyInNotebook


class Notebook(object):
    """Inject environment into a notebook"""
    def __init__(self, notebook):
        self.msg = ""
        self.notebook = notebook

    def inject(self, content, force=False):
        try:
            return self.store_in_file(content, force)
        except IOError:
            self.msg = "{} may not exist or you don't have adecuate permissions".format(self.notebook)
        except EnvironmentAlreadyInNotebook:
            self.msg = "There is already an environment in {}. Consider '--force'".\
                format(self.notebook)
        return False

    def store_in_file(self, content, force=False):
        with open(self.notebook) as fb:
            data = json.loads(fb.read())
            if force or 'environment' not in data['metadata']:
                data['metadata']['environment'] = content
            else:
                raise EnvironmentAlreadyInNotebook(self.notebook)

        with open(self.notebook, 'w') as fb:
            fb.write(json.dumps(data))
        return True


def current_env():
    """Retrieves dictionary with current environment's name and prefix"""
    if config.default_prefix == config.root_dir:
        name = config.root_env_name
    else:
        name = basename(config.default_prefix)
    return name
