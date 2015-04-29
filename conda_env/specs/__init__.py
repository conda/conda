from .binstar import BinstarSpec


def detect(**kwargs):
    for SpecClass in all_specs:
        spec = SpecClass(**kwargs)
        if spec.can_handle():
            return spec


all_specs = [
    BinstarSpec,
    # YamlFileSpec
]
