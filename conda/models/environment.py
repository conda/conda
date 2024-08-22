# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Models to specify input variables for the creation of conda environments

This could actually be merged with conda.core.prefix_data. They kind of have the same kind of scope.
"""

from __future__ import annotations

import json
import os
from dataclasses import InitVar, dataclass, field
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from ..base.constants import PREFIX_MAGIC_FILE, PREFIX_STATE_FILE, ChannelPriority
from ..base.context import context, validate_prefix_name
from ..common.path import is_package_file
from ..common.serialize import yaml_safe_load
from ..core.prefix_data import PrefixData
from ..core.solve import get_pinned_specs
from ..exceptions import (
    CondaValueError,
    DirectoryNotACondaEnvironmentError,
    DirectoryNotFoundError,
    NeedsNameOrPrefix,
)
from ..history import History
from .channel import Channel
from .match_spec import MatchSpec

if TYPE_CHECKING:
    from os import PathLike
    from typing import Any, Iterable

    from ..models.records import PrefixRecord

log = getLogger(__name__)


@dataclass
class SolverOptions:
    solver: str | None = None
    channel_priority: ChannelPriority | None = None

    def __post_init__(self):
        if self.solver is None:
            self.solver = context.solver
        if self.channel_priority is None:
            self.channel_priority = context.channel_priority

    def to_dict(self):
        return {
            "solver": self.solver,
            "channel_priority": self.channel_priority,
        }


@dataclass
class ChannelOptions:
    repodata_fns: str | Iterable[str] | None = None

    def __post_init__(self):
        if self.repodata_fns is None:
            self.repodata_fns = context.repodata_fns
        elif isinstance(self.repodata_fns, str):
            self.repodata_fns = [self.repodata_fns]

    def to_dict(self):
        return {
            "repodata_fns": self.repodata_fns,
        }


@dataclass
class Environment:
    _default_filename: ClassVar[str] = "conda.environment.yaml"
    _max_supported_version: ClassVar[int] = 2

    version: int = _max_supported_version
    name: str | None = None
    prefix: PathLike | None = None
    description: str | None = None
    last_modified: datetime | str | None = None
    channels: Iterable[Channel | str] | None = None
    channel_options: ChannelOptions = None
    requirements: Iterable[MatchSpec | str] | None = field(default_factory=list)
    # TODO: pip requirements are currently ignored, we need to decide the data structure
    constraints: Iterable[MatchSpec | str] | None = field(default_factory=list)
    solver_options: SolverOptions | None = None
    configuration: dict[str, Any] | None = field(default_factory=dict)
    variables: dict[str, str] | None = field(default_factory=dict)

    validate: InitVar[bool] = True

    def __post_init__(self, validate: bool):
        self.validate = validate
        if self.version > self._max_supported_version:
            raise ValueError(
                f"This conda version only supports schema versions up to "
                f"{self._max_supported_version}, but this one is version {self.version}. "
                "Try updating to a more recent conda to handle this input."
            )
        if self.name and not self.prefix:
            self.prefix = Path(validate_prefix_name(self.name, context))
        elif self.prefix:
            self.prefix = os.getcwd() / Path(self.prefix)
            if not self.name:
                self.name = self.prefix.name
        elif validate and not self.name and not self.prefix:
            raise NeedsNameOrPrefix("'Environment' needs either 'name' or 'prefix'.")
        if isinstance(self.channels, (str, Channel)):
            self.channels = [self.channels]
        elif self.channels is None:
            self.channels = context.channels if validate else []
        self.channels = [Channel(channel) for channel in self.channels]
        self.requirements = [MatchSpec(spec) for spec in self.requirements]
        self.constraints = [MatchSpec(spec) for spec in self.constraints]
        if validate and self.description is None:
            self.description = ""
        if validate and self.channel_options is None:
            self.channel_options = ChannelOptions()
        if validate and self.solver_options is None:
            self.solver_options = SolverOptions()
        if validate and self.last_modified is None:
            self.last_modified = datetime.now()
        if validate and isinstance(self.last_modified, str):
            self.last_modified = datetime.fromisoformat(self.last_modified)
        self._prefix_data = None

    @classmethod
    def merge(cls, *environments: Environment, validate: bool = True) -> Environment:
        """
        Keeps first name and/or prefix. Both if their basename match. Otherwise name wins.
        Keeps first description, channel_options, solver_options.
        Keeps max last_modified.
        Concatenates and deduplicates requirements and constraints.
        Reduces configuration and variables (last key wins).
        """
        name = None
        prefix = None
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
        if name and prefix and name != prefix.name:
            log.warning("Picked name %s and prefix %s do not match. Overriding prefix")
            prefix = None
        description = next(
            (env.description for env in environments if env.description), None
        )
        all_channel_options = [
            env.channel_options for env in environments if env.channel_options
        ]
        if all_channel_options:
            if all(
                all_channel_options[0] == options for options in all_channel_options[1:]
            ):
                channel_options = all_channel_options[0]
            elif validate:
                raise ValueError("All 'channel_options' fields must be equal.")
            else:
                log.warning(
                    "Different 'channel_options' detected. Keeping only first one..."
                )
                channel_options = all_channel_options[0]
        else:
            channel_options = None
        all_solver_options = [
            env.solver_options for env in environments if env.solver_options
        ]
        if all_solver_options:
            if all(
                all_solver_options[0] == options for options in all_solver_options[1:]
            ):
                solver_options = all_solver_options[0]
            elif validate:
                raise ValueError(
                    f"All 'solver_options' fields must be equal: {all_solver_options}"
                )
            else:
                log.warning(
                    "Different 'solver_options' detected. Keeping only first one..."
                )
                solver_options = all_solver_options[0]
        else:
            solver_options = None
        last_modified = max([env.last_modified or 0 for env in environments])
        channels = list(
            dict.fromkeys(channel for env in environments for channel in env.channels)
        )
        requirements = list(
            dict.fromkeys(
                requirement for env in environments for requirement in env.requirements
            )
        )
        constraints = list(
            dict.fromkeys(
                constraint for env in environments for constraint in env.constraints
            )
        )
        configuration = {
            k: v for env in environments for (k, v) in env.configuration.items()
        }
        variables = {k: v for env in environments for (k, v) in env.variables.items()}
        return cls(
            name=name,
            prefix=prefix,
            description=description,
            last_modified=last_modified,
            channels=channels,
            channel_options=channel_options,
            requirements=requirements,
            constraints=constraints,
            solver_options=solver_options,
            configuration=configuration,
            variables=variables,
            validate=validate,
        )

    @classmethod
    def from_prefix(
        cls,
        prefix: PathLike,
        validate: bool = True,
        load_history: bool = True,
        load_pins: bool = True,
    ) -> Environment:
        prefix = Path(prefix)
        if not prefix.is_dir():
            raise DirectoryNotFoundError(f"Prefix {prefix} is not a directory!")
        if (prefix / "conda-meta" / cls._default_filename).is_file():
            return cls.from_conda_meta(
                prefix / "conda-meta" / cls._default_filename, check_exists=False
            )

        if not (prefix / PREFIX_MAGIC_FILE).is_file():
            raise DirectoryNotACondaEnvironmentError(prefix)

        # This is an import from an old "history-only" conda environment

        name = prefix.name
        # TODO: Check with channels coming from PrefixData info?
        channels = context.channels
        channel_options = ChannelOptions()  # TODO: Check if this is saved anywhere
        last_modified = (prefix / PREFIX_MAGIC_FILE).stat().st_mtime
        if load_history:
            requirements = list(History(prefix).get_requested_specs_map().values())
        else:
            requirements = []
        if load_pins:
            constraints = get_pinned_specs(prefix)
        else:
            constraints = []
        solver_options = SolverOptions()  # TODO: Check if this is saved anywhere
        try:
            configuration = yaml_safe_load(prefix / "condarc")
        except OSError:
            configuration = {}
        try:
            variables = json.loads((prefix / PREFIX_STATE_FILE).read_text()).get(
                "env_vars"
            )
        except OSError:
            variables = {}
        return cls(
            name=name,
            prefix=prefix,
            description=f"Imported from '{prefix}' on {datetime.now()}",
            last_modified=last_modified,
            channels=channels,
            channel_options=channel_options,
            requirements=requirements,
            constraints=constraints,
            solver_options=solver_options,
            configuration=configuration,
            variables=variables,
            validate=validate,
        )

    @classmethod
    def from_conda_meta(
        cls, path: PathLike, check_exists: bool = True, validate: bool = True
    ):
        path = Path(path)
        if check_exists and not path.is_file():
            raise OSError(f"'{cls._default_filename}' file not found at {path}")
        with path.open() as f:
            data = yaml_safe_load(f)
        return cls(validate=validate, **data)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "version": self.version,
            "name": self.name,
            "prefix": str(self.prefix),
            "channels": self.channels,
            "channel_options": self.channel_options.to_dict(),
            "solver_options": self.solver_options.to_dict(),
        }
        if self.description:
            data["description"] = self.description
        if self.requirements:
            data["requirements"] = [str(spec) for spec in self.requirements]
        if self.constraints:
            data["constraints"] = [str(spec) for spec in self.constraints]
        if self.configuration:
            data["configuration"] = self.configuration
        if self.variables:
            data["variables"] = self.variables
        data["last_modified"] = datetime.now()
        return data

    def installed(self) -> Iterable[PrefixRecord]:
        assert self.exists(), f"Environment at '{self.prefix}' does not exist."
        if self._prefix_data is None:
            self._prefix_data = PrefixData(self.prefix)
        yield from self._prefix_data.iter_records()

    def exists(self) -> bool:
        return (
            self.prefix.is_dir() and (self.prefix / "conda-meta" / "history").is_file()
        )

    def is_explicit(self) -> bool:
        if not self.requirements:
            return False
        n_explicit = sum(1 for pkg in self.requirements if is_package_file(pkg))
        if n_explicit == len(self.requirements):
            return True
        if n_explicit == 0:
            return False
        raise CondaValueError(
            "cannot mix specifications with conda package URL / paths."
        )
