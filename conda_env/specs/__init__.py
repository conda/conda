# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os

from .binstar import BinstarSpec
from .notebook import NotebookSpec
from .requirements import RequirementsSpec
from .yaml_file import YamlFileSpec
from ..exceptions import (EnvironmentFileExtensionNotValid, EnvironmentFileNotFound,
                          SpecNotFound)


def detect(**kwargs):
    filename = kwargs.get('filename')
    remote_definition = kwargs.get('name')

    # Check extensions
    all_valid_exts = YamlFileSpec.extensions.union(RequirementsSpec.extensions)
    fname, ext = os.path.splitext(filename)

    # First check if file exists and test the known valid extension for specs
    file_exists = filename and os.path.isfile(filename)
    if file_exists:
        if ext == '' or ext not in all_valid_exts:
            raise EnvironmentFileExtensionNotValid(filename)
        elif ext in YamlFileSpec.extensions:
            specs = [YamlFileSpec]
        elif ext in RequirementsSpec.extensions:
            specs = [RequirementsSpec]
    else:
        specs = [NotebookSpec, BinstarSpec]

    # Check specifications
    spec_instances = []
    for SpecClass in specs:
        spec = SpecClass(**kwargs)
        spec_instances.append(spec)
        if spec.can_handle():
            return spec

    if not file_exists and remote_definition is None:
        raise EnvironmentFileNotFound(filename=filename)
    else:
        raise SpecNotFound(build_message(spec_instances))


def build_message(spec_instances):
    binstar_spec = next((s for s in spec_instances if isinstance(s, BinstarSpec)), None)
    if binstar_spec:
        return binstar_spec.msg
    else:
        return "\n".join([s.msg for s in spec_instances if s.msg is not None])
