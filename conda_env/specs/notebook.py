try:
    import nbformat
except ImportError:
    nbformat = None
from ..env import Environment
from .binstar import BinstarSpec


class NotebookSpec(object):
    msg = None

    def __init__(self, name=None, **kwargs):
        self.name = name
        self.nb = {}

    def can_handle(self):
        try:
            self.nb = nbformat.reader.reads(open(self.name).read())
            return 'environment' in self.nb['metadata']
        except AttributeError:
            self.msg = "Please install nbformat:\n\tconda install nbformat"
        except IOError:
            self.msg = "{} does not exist or can't be accessed".format(self.name)
        except (nbformat.reader.NotJSONError, KeyError):
            self.msg = "{} does not looks like a notebook file".format(self.name)
        except:
            return False
        return False

    @property
    def environment(self):
        if 'remote' in self.nb['metadata']['environment']:
            spec = BinstarSpec('darth/deathstar')
            return spec.environment
        else:
            return Environment(**self.nb['metadata']['environment'])
