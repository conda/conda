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
    # Check file existence
    filename = kwargs.get('filename')
    if filename and not os.path.isfile(filename):
        raise EnvironmentFileNotFound(filename=filename)

    # Check extensions
    all_valid_exts = YamlFileSpec.extensions.union(RequirementsSpec.extensions)
    fname, ext = os.path.splitext(filename)
    if ext == '' or ext not in all_valid_exts:
        raise EnvironmentFileExtensionNotValid(filename)
    elif ext in YamlFileSpec.extensions:
        specs = [YamlFileSpec]
    elif ext in RequirementsSpec.extensions:
        specs = [RequirementsSpec]
    else:
        specs = [NotebookSpec, BinstarSpec]

    # Check specifications
    for SpecClass in specs:
        spec = SpecClass(**kwargs)
        if spec.can_handle():
            return spec

    raise SpecNotFound(build_message(specs))


def build_message(specs):
    binstar_spec = next((spec for spec in specs if isinstance(spec, BinstarSpec)), None)
    if binstar_spec:
        return binstar_spec.msg
    else:
        return "\n".join([s.msg for s in specs if s.msg is not None])
