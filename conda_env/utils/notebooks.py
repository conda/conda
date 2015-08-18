from os.path import basename
import conda.config as config
from ..exceptions import EnvironmentAlreadyInNotebook, NBFormatNotInstalled
try:
    import nbformat
except ImportError:
    nbformat = None


class Notebook(object):
    """Inject environment into a notebook"""
    def __init__(self, notebook):
        self.msg = ""
        self.notebook = notebook
        if nbformat is None:
            raise NBFormatNotInstalled

    def inject(self, content, force=False):
        try:
            return self.store_in_file(content, force)
        except IOError:
            self.msg = "{} may not exist or you don't have adequate permissions".\
                format(self.notebook)
        except EnvironmentAlreadyInNotebook:
            self.msg = "There is already an environment in {}. Consider '--force'".\
                format(self.notebook)
        return False

    def store_in_file(self, content, force=False):
        nb = nbformat.reader.reads(open(self.notebook).read())
        if force or 'environment' not in nb['metadata']:
            nb['metadata']['environment'] = content
            nbformat.write(nb, self.notebook)
            return True
        else:
            raise EnvironmentAlreadyInNotebook(self.notebook)


def current_env():
    """Retrieves dictionary with current environment's name and prefix"""
    if config.default_prefix == config.root_dir:
        name = config.root_env_name
    else:
        name = basename(config.default_prefix)
    return name
