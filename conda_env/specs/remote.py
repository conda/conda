# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Remote spec using fsspec"""
from functools import cached_property

import fsspec
from fsspec import available_protocols
from fsspec.core import split_protocol

from ..env import Environment, from_yaml


class RemoteSpec:
    """
    spec = RemoteSpec('protocol://path/to/environment-yaml')
    spec.can_handle() # => True / False
    spec.environment # => YAML string
    spec.msg # => Error messages
    """

    msg = None

    def __init__(self, uri=None):
        self.uri = uri

    def can_handle(self) -> bool:
        """Determine if the requested protocol is installed"""
        protocol, _ = split_protocol(self.uri)
        if protocol not in available_protocols():
            self.msg = (
                f"You need to install the package that provides"
                f" the FSSpec {protocol} protocol."
            )
            return False
        return True

    @cached_property
    def environment(self) -> Environment:
        with fsspec.open(self.uri, "rt") as f:
            data = f.read()
        return from_yaml(data)
