# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""EXPERIMENTAL Conda environment data model"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from functools import reduce
from itertools import chain
from logging import getLogger
from typing import TYPE_CHECKING

from ..base.constants import EXPLICIT_MARKER, PLATFORMS, UNKNOWN_CHANNEL
from ..base.context import context

# TODO: this cli import will be removed once the Environment.from_cli method
# is updated to use the environment spec plugins to read environment files.
from ..cli.common import specs_from_url
from ..common.iterators import groupby_to_dict as groupby
from ..core.prefix_data import PrefixData
from ..exceptions import CondaError, CondaValueError
from ..history import History
from ..misc import get_package_records_from_explicit
from .match_spec import MatchSpec

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable
    from typing import TypeVar

    from ..base.constants import (
        ChannelPriority,
        DepsModifier,
        SatSolverChoice,
        UpdateModifier,
    )
    from ..common.path import PathType
    from .records import PackageRecord

    T = TypeVar("T")

log = getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """
    **Experimental** While experimental, expect both major and minor changes across minor releases.

    Data model for a conda environment config.
    """

    aggressive_update_packages: tuple[str, ...] = field(default_factory=tuple)

    channel_priority: ChannelPriority | None = None

    channels: tuple[str, ...] = field(default_factory=tuple)

    channel_settings: tuple[dict[str, str], ...] = field(default_factory=tuple)

    deps_modifier: DepsModifier | None = None

    disallowed_packages: tuple[str, ...] = field(default_factory=tuple)

    pinned_packages: tuple[str, ...] = field(default_factory=tuple)

    repodata_fns: tuple[str, ...] = field(default_factory=tuple)

    sat_solver: SatSolverChoice | None = None

    solver: str | None = None

    track_features: tuple[str, ...] = field(default_factory=tuple)

    update_modifier: UpdateModifier | None = None

    use_only_tar_bz2: bool | None = None

    def _append_without_duplicates(
        self, first: Iterable[T], second: Iterable[T]
    ) -> tuple[T, ...]:
        return tuple(dict.fromkeys(item for item in chain(first, second)))

    def _merge_channel_settings(
        self, first: tuple[dict[str, str], ...], second: tuple[dict[str, str], ...]
    ) -> tuple[dict[str, str], ...]:
        """Merge channel settings.

        An individual channel setting is a dict that may have the key "channels". Settings
        with matching "channels" should be merged together.
        """

        grouped_channel_settings = groupby(
            lambda x: x.get("channel"), chain(first, second)
        )

        return tuple(
            {k: v for config in configs for k, v in config.items()}
            for channel, configs in grouped_channel_settings.items()
        )

    def _merge(self, other: EnvironmentConfig) -> EnvironmentConfig:
        """
        **Experimental** While experimental, expect both major and minor changes across minor releases.

        Merges an EnvironmentConfig into this one. Merging rules are:
        * Primitive types get clobbered if subsequent configs have a value, otherwise keep the last set value
        * Lists get appended to and deduplicated
        * Dicts get updated
        * Special cases:
          * channel settings is a list of dicts, it merges inner dicts, keyed on "channel"
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

        self.channel_settings = self._merge_channel_settings(
            self.channel_settings, other.channel_settings
        )

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
        if not configs:
            return

        # If there is only one config, there is nothing to merge, return the lone config
        if len(configs) == 1:
            return configs[0]

        # Use reduce to merge all configs into the first one
        return reduce(
            lambda result, config: result._merge(config), configs[1:], configs[0]
        )


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

    # Virtual packages for the environment. Either the default ones provided by
    # the virtual_packages plugins or the overrides captured by CONDA_OVERRIDE_*.
    virtual_packages: list[PackageRecord] = field(default_factory=list)

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

        virtual_packages = list(
            dict.fromkeys(
                virtual_package
                for env in environments
                for virtual_package in env.virtual_packages
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
            virtual_packages=virtual_packages,
        )

    @classmethod
    def from_prefix(
        cls,
        prefix: str,
        name: str,
        platform: str,
        *,
        from_history: bool = False,
        no_builds: bool = False,
        ignore_channels: bool = False,
        channels: list[str] | None = None,
    ) -> Environment:
        """
        Create an Environment model from an existing conda prefix.

        This method analyzes an installed conda environment and creates
        an Environment model that can be used for exporting or other operations.

        :param prefix: Path to the conda environment prefix
        :param name: Name for the environment
        :param platform: Target platform (e.g., 'linux-64', 'osx-64')
        :param from_history: Use explicit specs from history instead of installed packages
        :param no_builds: Exclude build strings from package specs
        :param ignore_channels: Don't include channel information in package specs
        :return: Environment model representing the prefix
        """
        prefix_data = PrefixData(prefix, interoperability=True)
        variables = prefix_data.get_environment_env_vars()

        # Build requested packages and external packages
        requested_packages = []
        external_packages = {}

        # Handle --from-history case
        if from_history:
            requested_packages = cls.from_history(prefix)
            conda_precs = []  # No conda packages to process for channel extraction
        else:
            # Use PrefixData's package extraction methods
            conda_precs = prefix_data.get_conda_packages()
            python_precs = prefix_data.get_python_packages()

            # Create MatchSpecs for conda packages
            for conda_prec in conda_precs:
                spec_str = conda_prec.spec_no_build if no_builds else conda_prec.spec

                if (
                    not ignore_channels
                    and conda_prec.channel
                    and conda_prec.channel.name
                ):
                    spec_str = f"{conda_prec.channel.name}::{spec_str}"

                requested_packages.append(MatchSpec(spec_str))

            # Add pip dependencies to external_packages if any exist
            if python_precs:
                # Create pip dependencies list matching current conda format
                python_deps = [
                    f"{python_prec.name}=={python_prec.version}"
                    for python_prec in python_precs
                ]
                external_packages["pip"] = python_deps

        # Always populate explicit_packages from prefix data (for explicit export format)
        explicit_packages = list(prefix_data.iter_records())

        # Build channels list
        environment_channels = list(channels or [])

        # Inject channels from installed conda packages (unless ignoring channels)
        # This applies regardless of override_channels setting
        if not ignore_channels:
            environment_channels = (
                *(
                    canonical_name
                    # Reuse conda_precs instead of calling get_conda_packages() again
                    for conda_package in conda_precs
                    if (canonical_name := conda_package.channel.canonical_name)
                    != UNKNOWN_CHANNEL
                ),
                *environment_channels,
            )

        # Channel list is a unique ordered list
        environment_channels = list(dict.fromkeys(environment_channels))

        # Create environment config with comprehensive context settings
        config = EnvironmentConfig.from_context()

        # Override/set channels with those extracted from installed packages if any were found
        config = replace(config, channels=tuple(environment_channels))

        return cls(
            prefix=prefix,
            platform=platform,
            name=name,
            config=config,
            variables=variables,
            external_packages=external_packages,
            requested_packages=requested_packages,
            explicit_packages=explicit_packages,
        )

    @classmethod
    def from_cli(
        cls,
        args: Namespace,
        add_default_packages: bool = False,
    ) -> Environment:
        """
        Create an Environment model from command-line arguments.

        This method will parse command-line arguments and create an
        Environment object. This includes: reading files provided as
        cli arguments, and pulling EnvironmentConfig from the context.

        :param args: argparse Namespace containing command-line arguments
        :return: An Environment object representing the cli
        """
        specs = [package.strip("\"'") for package in args.packages]
        requested_packages = []
        fetch_explicit_packages = []

        # extract specs from files
        # TODO: This should be replaced with reading files using the
        # environment spec plugin. The core conda cli commands are not
        # ready for that yet. So, use this old way of reading specs from
        # files.
        for fpath in args.file:
            try:
                specs.extend(
                    [spec for spec in specs_from_url(fpath) if spec != EXPLICIT_MARKER]
                )
            except UnicodeError:
                raise CondaError(
                    "Error reading file, file should be a text file containing packages\n"
                    "See `conda create --help` for details."
                )

        # Add default packages if required. If the default package is already
        # present in the list of specs, don't add it (this will override any
        # version constraint from the default package).
        if add_default_packages:
            names = {MatchSpec(spec).name for spec in specs}
            for default_package in context.create_default_packages:
                if MatchSpec(default_package).name not in names:
                    specs.append(default_package)

        for spec in specs:
            if (match_spec := MatchSpec(spec)).get("url"):
                fetch_explicit_packages.append(spec)
            else:
                requested_packages.append(match_spec)

        # transform explicit packages into package records
        explicit_packages = []
        if fetch_explicit_packages:
            if len(fetch_explicit_packages) == len(specs):
                explicit_packages = get_package_records_from_explicit(
                    fetch_explicit_packages
                )
            else:
                raise CondaValueError(
                    "Cannot mix specifications with conda package filenames"
                )

        return Environment(
            name=args.name,
            prefix=context.target_prefix,
            platform=context.subdir,
            requested_packages=requested_packages,
            explicit_packages=explicit_packages,
            config=EnvironmentConfig.from_context(),
        )

    @staticmethod
    def from_history(prefix: PathType) -> list[MatchSpec]:
        history = History(prefix)
        spec_map = history.get_requested_specs_map()
        # Get MatchSpec objects from history; they'll be serialized to bracket format later
        return list(spec_map.values())

    def extrapolate(self, platform: str) -> Environment:
        """
        Given the current environment, extrapolate the environment for the given platform.
        """
        if platform == self.platform:
            return self

        from ..cli.install import Repodatas

        solver_backend = context.plugin_manager.get_cached_solver_backend()
        requested_packages = self.from_history(self.prefix)

        for repodata_manager in Repodatas(self.config.repodata_fns, {}):
            with repodata_manager as repodata_fn:
                solver = solver_backend(
                    prefix="/env/does/not/exist",
                    channels=context.channels,
                    subdirs=(platform, "noarch"),
                    specs_to_add=requested_packages,
                    repodata_fn=repodata_fn,
                    command="create",
                )
                explicit_packages = solver.solve_final_state()
        return Environment(
            prefix=self.prefix,
            name=self.name,
            platform=platform,
            config=EnvironmentConfig.from_context(),
            requested_packages=requested_packages,
            explicit_packages=explicit_packages,
            external_packages=self.external_packages,
        )
