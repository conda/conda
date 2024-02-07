# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Test for configuration parameters plugin hook"""
from .. import CondaConfigurationParameter, hookimpl


@hookimpl
def conda_configuration_parameters():
    from conda.common.configuration import ParameterLoader, PrimitiveParameter

    loader = ParameterLoader(PrimitiveParameter("", element_type=str))

    yield CondaConfigurationParameter(
        name="my_plugin",
        description="test parameter",
        loader=loader,
    )
