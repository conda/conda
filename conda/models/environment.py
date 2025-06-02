# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""EXPERIMENTAL Conda environment data model"""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import getLogger
from typing import TYPE_CHECKING

from ..base.constants import PLATFORMS
from ..exceptions import CondaValueError

if TYPE_CHECKING:
    from typing import Any

    from .match_spec import MatchSpec
    from .records import PackageRecord


log = getLogger(__name__)


@dataclass
class Environment:
    """
    **Experimental** While experimental, expect both major and minor changes across minor releases.

    Data model for a conda environment.
    """

    #: Prefix the environment is installed into (required).
    prefix: str

    #: The platform this environment may be installed on (required)
    platform: str

    #: Environment level configuration, eg. channels, solver options, etc.
    #: TODO: may need to think more about the type of this field and how
    #:       conda should be merging configs between environments
    config: dict[str, Any] = field(default_factory=dict)

    #: Map of other package types that conda can install. For example pypi packages.
    external_packages: dict[str, list[str]] = field(default_factory=dict)

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

        # an environment must have a platform
        if not self.platform:
            raise CondaValueError("'Environment' needs a 'platform'.")
        
        # ensure the platform is valid
        if self.platform not in PLATFORMS:
            raise CondaValueError(f"Invalid platform '{self.platform}'. Valid platforms are {PLATFORMS}.")

        # ensure there are no duplicate packages in explicit_packages
        if len(self.explicit_packages) > 1 and len(set(pkg.name for pkg in self.explicit_packages)) != len(self.explicit_packages):
            raise CondaValueError("Duplicate packages found in 'explicit_packages'.")
        
        # ensure requested_packages matches one (and only one) explicit package
        if len(self.requested_packages) > 0 and len(self.explicit_packages) > 0:
            explicit_package_names = set(pkg.name for pkg in self.explicit_packages)
            for requested_package in self.requested_packages:
                if requested_package.name not in explicit_package_names:
                    raise CondaValueError(f"Requested package '{requested_package}' is not found in 'explicit_packages'.")


    @classmethod
    def merge(cls, *environments):
        """
        **Experimental** While experimental, expect both major and minor changes across minor releases.

        Merges multiple environments into a single environment following the rules:
        * Keeps first name and/or prefix.
        * Concatenates and deduplicates requirements.
        * Reduces configuration and variables (last key wins).
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
                "Conda can not merge environments of different platforms. "
                f"Received environments with platforms: {platforms}"
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
            # we'll want to concatenate each list.
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
