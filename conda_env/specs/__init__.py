from .binstar import BinstarSpec
from .yaml_file import YamlFileSpec
from .notebook import NotebookSpec
from ..exceptions import SpecNotFound

all_specs = [
    BinstarSpec,
    NotebookSpec,
    YamlFileSpec
]


def detect(**kwargs):
    specs = []
    for SpecClass in all_specs:
        spec = SpecClass(**kwargs)
        specs.append(spec)
        if spec.can_handle():
            return spec

    raise SpecNotFound(build_message(specs))


def build_message(specs):
    return "\n".join([s.msg for s in specs if s.msg is not None])
