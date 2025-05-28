# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda environment data model"""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import getLogger
from typing import TYPE_CHECKING

from ..exceptions import CondaValueError

if TYPE_CHECKING:
    from typing import Any

    from .match_spec import MatchSpec
    from .records import PackageRecord


log = getLogger(__name__)


@dataclass
class Environment:
    #: Prefix the environment is installed into (required).
    prefix: str

    #: The platform this environment may be installed on (required)
    platform: str

    #: Environment level configuration, eg. channels, solver options, etc.
    config: dict[str, Any] = field(default_factory=dict)

    #: Map of other package types that conda can install. For example pypi packages.
    external_packages: dict[str, list[Any]] = field(default_factory=dict)

    #: The complete list of specs for the environment.
    #: eg. after a solve, or from an explicit environemnt spec
    explicit_packages: list[PackageRecord] = field(default_factory=list)

    #: Environment name
    name: str | None = None

    #: User requested specs for this environment.
    requested_packages: list[MatchSpec] = field(default_factory=list)

    #: Environment variables to be applied to the environment.
    variables: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        # an environment must have a name of prefix
        if not self.prefix:
            raise CondaValueError("'Environment' needs a 'prefix'.")

    @classmethod
    def merge(cls, *environments):
        """
        Keeps first name and/or prefix.
        Concatenates and deduplicates requirements.
        Reduces configuration and variables (last key wins).
        """
        name = None
        prefix = None
        platform = None
        names = [env.name for env in environments if env.name]
        prefixes = [env.prefix for env in environments if env.prefix]

        if names:
            name = names[0]
            if len(names) > 1:
                log.debug("Several names passed %s. Picking first one %s", names, name)

        if prefixes:
            prefix = prefixes[0]
            if len(prefixes) > 1:
                log.debug(
                    "Several prefixes passed %s. Picking first one %s", prefixes, prefix
                )

        platforms = [env.platform for env in environments if env.platform]
        # Ensure that all environments have the same platform
        if len(set(platforms)) == 1:
            platform = platforms[0]
        else:
            raise CondaValueError(
                f"Conda can not merge environments of different platforms. Recieved environments with plafroms {platforms}"
            )

        requested_packages = list(
            dict.fromkeys(
                requirement
                for env in environments
                for requirement in env.requested_packages
            )
        )

        explicit_packages = list(
            dict.fromkeys(
                requirement
                for env in environments
                for requirement in env.explicit_packages
            )
        )

        variables = {k: v for env in environments for (k, v) in env.variables.items()}

        config = {}
        external_packages = {}
        for env in environments:
            # Config items can be any type, merge them so that lists get
            # concatenated, dicts get merged, and primitive types get clobbered.
            for k, v in env.config.items():
                if k not in config:
                    config[k] = v
                elif isinstance(config[k], list) and isinstance(v, list):
                    config[k].extend(v)
                elif isinstance(config[k], dict) and isinstance(v, dict):
                    config[k].update(v)
                else:
                    log.debug("merging configs, clobbering value %s with value %s")
                    config[k] = v

            # External packages map values are always lists of strings. So,
            # we'll want to concatentate each list.
            for k, v in env.external_packages.items():
                if k in external_packages:
                    for val in v:
                        if val not in external_packages[k]:
                            external_packages[k].append(val)
                elif isinstance(v, list):
                    external_packages[k] = v

        return cls(
            config=config,
            external_packages=external_packages,
            explicit_packages=explicit_packages,
            name=name,
            platform=platform,
            prefix=prefix,
            requested_packages=requested_packages,
            variables=variables,
        )
