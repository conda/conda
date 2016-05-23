# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from logging import getLogger

from auxlib.ish import dals

from ..common.configuration import (Configuration as AppConfiguration, Parameter, ParameterType,
                                    load_raw_configs)
from .constants import SEARCH_PATH

log = getLogger(__name__)


class Context(AppConfiguration):

    add_pip_as_python_dependency = Parameter(default=True)
    always_yes = Parameter(False)
    always_copy = Parameter(False)
    changeps1 = Parameter(True)
    use_pip = Parameter(True)
    binstar_upload = Parameter(None, aliases=('anaconda_upload', ))
    allow_softlinks = Parameter(True)
    self_update = Parameter(True)
    show_channel_urls = Parameter(None)
    update_dependencies = Parameter(True)
    channel_priority = Parameter(True)
    ssl_verify = Parameter(True)
    track_features = Parameter((), parameter_type=ParameterType.list)
    channels = Parameter((), parameter_type=ParameterType.list)
    disallow = Parameter((), parameter_type=ParameterType.list)
    create_default_packages = Parameter((), parameter_type=ParameterType.list)
    envs_dirs = Parameter((), parameter_type=ParameterType.list)
    default_channels = Parameter((), parameter_type=ParameterType.list)
    proxy_servers = Parameter({}, parameter_type=ParameterType.map)


context = Context(load_raw_configs(SEARCH_PATH))


def get_help_dict():
    # this is a function so that most of the time it's not evaluated and loaded into memory
    return {
        'add_pip_as_python_dependency': dals("""
            """),
        'always_yes': dals("""
            """),
        'always_copy': dals("""
            """),
        'changeps1': dals("""
            """),
        'use_pip': dals("""
            Use pip when listing packages with conda list. Note that this does not affect any
            conda command or functionality other than the output of the command conda list.
            """),
        'binstar_upload': dals("""
            """),
        'allow_softlinks': dals("""
            """),
        'self_update': dals("""
            """),
        'show_channel_urls': dals("""
            # show channel URLs when displaying what is going to be downloaded
            # None means letting conda decide
            """),
        'update_dependencies': dals("""
            """),
        'channel_priority': dals("""
            """),
        'ssl_verify': dals("""
            # ssl_verify can be a boolean value or a filename string
            """),
        'track_features': dals("""
            """),
        'channels': dals("""
            """),
        'disallow': dals("""
            # set packages disallowed to be installed
            """),
        'create_default_packages': dals("""
            # packages which are added to a newly created environment by default
            """),
        'envs_dirs': dals("""
            """),
        'default_channels': dals("""
            """),
        'proxy_servers': dals("""
            """),
    }

