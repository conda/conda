# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from getpass import getpass

from requests.auth import HTTPBasicAuth

from conda import plugins
from conda.common.compat import string_types
from conda.common.configuration import ParameterLoader, PrimitiveParameter, SequenceParameter

CACHED_CREDENTIALS = {}


def get_channel_credentials(channel: str = "Channel Name") -> tuple[str, str]:
    print(f"Please provide credentials for: {channel}")
    username = input("Username: ")
    password = getpass("Password: ")

    return username, password


def conda_session_manager(channel: str = "Channel Name") -> "CondaSession":
    """
    Overrides the default session manager so that we can provide
    CondaSessions with `requests.auth.HTTPBasicAuth` objects attached to them.
    """
    from conda.base.context import context
    from conda.gateways.connection.session import CondaSession

    session = CondaSession()

    if channel is not None and channel in context.authenticated_channels:
        credentials = CACHED_CREDENTIALS.get(channel)

        if not credentials:
            credentials: tuple = get_channel_credentials(channel)
            CACHED_CREDENTIALS[channel] = credentials

        session.auth = HTTPBasicAuth(*credentials)

    return session


@plugins.hookimp
def get_conda_session_manager() -> plugins.CondaSessionManager:
    return conda_session_manager


@plugins.hookimp
def extend_context() -> plugins.CondaContextExtension:
    """
    Registers a function that returns a callable which accepts the Context class.
    This callable then mutates that class to add new configuration paramters.

    Using `setattr`, we can begin adding arbitrary new parameters to the Context
    object. We do need to call the `_set_name` method on the `ParameterLoader`
    object after instantiating it. This is contrary to what is recommended in
    the doc string for this method.

    Overall this is pretty gross, and I would never expect a plugin author to
    write this much boilerplate, but it does prove it can be done!

    What this still doesn't do:

    - Update the `Context.category_map`
    - Update the `Context.description_map`

    These two methods would need to be refactored to accommodate our use case
    here. For example, the `description_map` currently defines a `frozendict` that
    we would want to change to a regular, mutable `dict`.

    Also, this implementation would completely clobber existing configuration
    options, which we would not want to allow. Once we refactor the two map method
    we would want to build another layer of abstraction over this that would make
    defining these parameters easier while also adding validation and sensible
    errors to make sure plugin authors are extending the context object correctly.
    """

    def _extend_context(context_class: type) -> None:
        name = "authenticated_channels"
        param = ParameterLoader(
            SequenceParameter(PrimitiveParameter(name, element_type=string_types)), aliases=(name,)
        )
        name = param._set_name(name)
        setattr(context_class, name, param)

        # This is done in the `ConfigurationType` metaclass, so we make sure to do it here too
        setattr(context_class, "parameter_names", context_class.parameter_names + (name,))

    return _extend_context
