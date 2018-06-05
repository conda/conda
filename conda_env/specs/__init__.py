# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# Standard library imports
import os

# Local imports
from .binstar import BinstarSpec
from .notebook import NotebookSpec
from .requirements import RequirementsSpec
from .yaml_file import YamlFileSpec
from ..exceptions import EnvironmentFileNotFound, SpecNotFound


all_specs = [
    BinstarSpec,
    NotebookSpec,
    YamlFileSpec,
    RequirementsSpec
]


def detect(**kwargs):
    # Check file existence if --file was provided
    filename = kwargs.get('filename')
    if filename and not os.path.isfile(filename):
        raise EnvironmentFileNotFound(filename=filename)

    # Check specifications
    specs = []
    for SpecClass in all_specs:
        spec = SpecClass(**kwargs)
        specs.append(spec)
        if spec.can_handle():
            return spec

    raise SpecNotFound(build_message(specs))


def build_message(specs):
    binstar_spec = next((spec for spec in specs if isinstance(spec, BinstarSpec)), None)
    if binstar_spec:
        return binstar_spec.msg
    else:
        return "\n".join([s.msg for s in specs if s.msg is not None])
