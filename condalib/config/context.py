# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from logging import getLogger

from auxlib.ish import dals
from auxlib.compat import string_types

from ..common.configuration import (Configuration as AppConfiguration, PrimitiveParameter,
                                    SequenceParameter, MapParameter)
from .constants import SEARCH_PATH

log = getLogger(__name__)


class Context(AppConfiguration):

    add_pip_as_python_dependency = PrimitiveParameter(True)
    always_yes = PrimitiveParameter(False)
    always_copy = PrimitiveParameter(False)
    changeps1 = PrimitiveParameter(True)
    use_pip = PrimitiveParameter(True)
    binstar_upload = PrimitiveParameter(None, aliases=('anaconda_upload', ))
    allow_softlinks = PrimitiveParameter(True)
    self_update = PrimitiveParameter(True)
    show_channel_urls = PrimitiveParameter(None)
    update_dependencies = PrimitiveParameter(True)
    channel_priority = PrimitiveParameter(True)
    ssl_verify = PrimitiveParameter(True)
    track_features = SequenceParameter(string_types)
    channels = SequenceParameter(string_types)
    disallow = SequenceParameter(string_types)
    create_default_packages = SequenceParameter(string_types)
    envs_dirs = SequenceParameter(string_types)
    default_channels = SequenceParameter(string_types)
    proxy_servers = MapParameter(string_types)


context = Context.from_search_path(SEARCH_PATH)


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

