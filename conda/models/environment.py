# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""EXPERIMENTAL Conda environment data model"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from logging import getLogger
from typing import TYPE_CHECKING

from ..base.constants import PLATFORMS
from ..base.context import context
from ..exceptions import CondaValueError

if TYPE_CHECKING:
    from ..base.constants import (
        ChannelPriority,
        DepsModifier,
        SatSolverChoice,
        UpdateModifier,
    )
    from .match_spec import MatchSpec
    from .records import PackageRecord


log = getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """
    **Experimental** While experimental, expect both major and minor changes across minor releases.

    Data model for a conda environment config.
    """

    aggressive_update_packages: list[str] = field(default_factory=list)

    channel_priority: ChannelPriority | None = None

    channels: list[str] = field(default_factory=list)

    channel_settings: dict[str, str] = field(default_factory=dict)

    deps_modifier: DepsModifier | None = None

    disallowed_packages: list[str] = field(default_factory=list)

    pinned_packages: list[str] = field(default_factory=list)

    repodata_fns: list[str] = field(default_factory=list)

    sat_solver: SatSolverChoice | None = None

    solver: str | None = None

    track_features: list[str] = field(default_factory=list)

    update_modifier: UpdateModifier | None = None

    use_only_tar_bz2: bool | None = None

    def _append_without_duplicates(self, first: list, second: list) -> list:
        first.extend(second)
        return list(dict.fromkeys(item for item in first))

    def _merge(self, other: EnvironmentConfig) -> EnvironmentConfig:
        """
        **Experimental** While experimental, expect both major and minor changes across minor releases.

        Merges an EnvironmentConfig into this one. Merging rules are:
        * Primitive types get clobbered if subsequent configs have a value, otherwise keep the last set value
        * Lists get appended to and deduplicated
        * Dicts get updated
        """
        # Return early if there is nothing to merge
        if other is None:
            return self

        # Ensure that we are merging another EnvironmentConfig
        if not isinstance(other, self.__class__):
            raise CondaValueError(
                "Cannot merge EnvironmentConfig with non-EnvironmentConfig"
            )

        self.aggressive_update_packages = self._append_without_duplicates(
            self.aggressive_update_packages, other.aggressive_update_packages
        )

        if other.channel_priority is not None:
            self.channel_priority = other.channel_priority

        self.channels = self._append_without_duplicates(self.channels, other.channels)

        self.channel_settings.update(other.channel_settings)

        if other.deps_modifier is not None:
            self.deps_modifier = other.deps_modifier

        self.disallowed_packages = self._append_without_duplicates(
            self.disallowed_packages, other.disallowed_packages
        )

        self.pinned_packages = self._append_without_duplicates(
            self.pinned_packages, other.pinned_packages
        )

        self.repodata_fns = self._append_without_duplicates(
            self.repodata_fns, other.repodata_fns
        )

        if other.sat_solver is not None:
            self.sat_solver = other.sat_solver

        if other.solver is not None:
            self.solver = other.solver

        self.track_features = self._append_without_duplicates(
            self.track_features, other.track_features
        )

        if other.update_modifier is not None:
            self.update_modifier = other.update_modifier

        if other.use_only_tar_bz2 is not None:
            self.use_only_tar_bz2 = other.use_only_tar_bz2

        return self

    @classmethod
    def from_context(cls) -> EnvironmentConfig:
        """
        **Experimental** While experimental, expect both major and minor changes across minor releases.

        Create an EnvironmentConfig from the current context
        """
        field_names = {field.name for field in fields(cls)}

        environment_settings = {
            key: value
            for key, value in context.environment_settings.items()
            if key in field_names
        }
        return cls(**environment_settings)

    @classmethod
    def merge(cls, *configs: EnvironmentConfig) -> EnvironmentConfig:
        """
        **Experimental** While experimental, expect both major and minor changes across minor releases.

        Merges a list of EnvironmentConfigs into a single one. Merging rules are:
        * Primitive types get clobbered if subsequent configs have a value, otherwise keep the last set value
        * Lists get appended to and deduplicated
        * Dicts get updated
        """

        # Don't try to merge if there is nothing to merge
        if len(configs) == 0:
            return

        # If there is only one config, there is nothing to merge, return the lone config
        if len(configs) == 1:
            return configs[0]

        result = EnvironmentConfig()
        for config in configs:
            result._merge(config)
        return result


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
    config: EnvironmentConfig = field(default_factory=EnvironmentConfig)

    #: Map of other package types that conda can install. For example pypi packages.
    external_packages: dict[str, list[str]] = field(default_factory=dict)

    #: The complete list of specs for the environment.
    #: eg. after a solve, or from an explicit environment spec
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
            raise CondaValueError(
                f"Invalid platform '{self.platform}'. Valid platforms are {PLATFORMS}."
            )

        # ensure there are no duplicate packages in explicit_packages
        if len(self.explicit_packages) > 1 and len(
            set(pkg.name for pkg in self.explicit_packages)
        ) != len(self.explicit_packages):
            raise CondaValueError("Duplicate packages found in 'explicit_packages'.")

        # ensure requested_packages matches one (and only one) explicit package
        if len(self.requested_packages) > 0 and len(self.explicit_packages) > 0:
            explicit_package_names = set(pkg.name for pkg in self.explicit_packages)
            for requested_package in self.requested_packages:
                if requested_package.name not in explicit_package_names:
                    raise CondaValueError(
                        f"Requested package '{requested_package}' is not found in 'explicit_packages'."
                    )

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

        external_packages = {}
        for env in environments:
            # External packages map values are always lists of strings. So,
            # we'll want to concatenate each list.
            for k, v in env.external_packages.items():
                if k in external_packages:
                    for val in v:
                        if val not in external_packages[k]:
                            external_packages[k].append(val)
                elif isinstance(v, list):
                    external_packages[k] = v

        config = EnvironmentConfig.merge(
            *[env.config for env in environments if env.config is not None]
        )

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
