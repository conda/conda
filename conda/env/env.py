# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Environment object describing the conda environment.yaml file."""

from __future__ import annotations

import json
import os
import re
import textwrap
from abc import ABC
from collections.abc import Iterable
from functools import total_ordering
from itertools import chain
from os.path import abspath, basename, dirname, expanduser, expandvars
from typing import TYPE_CHECKING

from ..base.constants import ROOT_ENV_NAME
from ..base.context import context
from ..cli import common, install
from ..common.iterators import groupby_to_dict as groupby
from ..common.iterators import unique
from ..common.path import paths_equal
from ..common.serialize import yaml_safe_dump, yaml_safe_load
from ..core.prefix_data import PrefixData
from ..exceptions import EnvironmentFileEmpty, EnvironmentFileNotFound
from ..gateways.connection.download import download_text
from ..gateways.connection.session import CONDA_SESSION_SCHEMES
from ..history import History
from ..models.enums import PackageType
from ..models.match_spec import MatchSpec
from ..models.prefix_graph import PrefixGraph

if TYPE_CHECKING:
    import io
    from collections.abc import Mapping
    from typing import Any

VALID_KEYS = ("name", "dependencies", "prefix", "channels", "variables")


def validate_keys(data, kwargs):
    """Check for unknown keys, remove them and print a warning"""
    invalid_keys = []
    new_data = data.copy() if data else {}
    for key in data.keys():
        if key not in VALID_KEYS:
            invalid_keys.append(key)
            new_data.pop(key)

    if invalid_keys:
        filename = kwargs.get("filename")
        verb = "are" if len(invalid_keys) != 1 else "is"
        plural = "s" if len(invalid_keys) != 1 else ""
        print(
            f"\nEnvironmentSectionNotValid: The following section{plural} on "
            f"'{filename}' {verb} invalid and will be ignored:"
        )
        for key in invalid_keys:
            print(f" - {key}")
        print()

    deps = data.get("dependencies", [])
    depsplit = re.compile(r"[<>~\s=]")
    is_pip = lambda dep: "pip" in depsplit.split(dep)[0].split("::")
    lists_pip = any(is_pip(dep) for dep in deps if not isinstance(dep, dict))
    for dep in deps:
        if isinstance(dep, dict) and "pip" in dep and not lists_pip:
            print(
                "Warning: you have pip-installed dependencies in your environment file, "
                "but you do not list pip itself as one of your conda dependencies.  Conda "
                "may not use the correct pip to install your packages, and they may end up "
                "in the wrong place.  Please add an explicit pip dependency.  I'm adding one"
                " for you, but still nagging you."
            )
            new_data["dependencies"].insert(0, "pip")
            break
    return new_data


def from_environment(
    name, prefix, no_builds=False, ignore_channels=False, from_history=False
):
    """
        Get ``Environment`` object from prefix
    Args:
        name: The name of environment
        prefix: The path of prefix
        no_builds: Whether has build requirement
        ignore_channels: whether ignore_channels
        from_history: Whether environment file should be based on explicit specs in history

    Returns:     Environment object
    """
    pd = PrefixData(prefix, interoperability=True)
    variables = pd.get_environment_env_vars()

    if from_history:
        history = History(prefix).get_requested_specs_map()
        deps = [str(package) for package in history.values()]
        return Environment(
            name=name,
            dependencies=deps,
            channels=list(context.channels),
            prefix=prefix,
            variables=variables,
        )

    precs = tuple(PrefixGraph(pd.iter_records()).graph)
    grouped_precs = groupby(lambda x: x.package_type, precs)
    conda_precs = sorted(
        (
            *grouped_precs.get(None, ()),
            *grouped_precs.get(PackageType.NOARCH_GENERIC, ()),
            *grouped_precs.get(PackageType.NOARCH_PYTHON, ()),
        ),
        key=lambda x: x.name,
    )

    pip_precs = sorted(
        (
            *grouped_precs.get(PackageType.VIRTUAL_PYTHON_WHEEL, ()),
            *grouped_precs.get(PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE, ()),
            *grouped_precs.get(PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE, ()),
        ),
        key=lambda x: x.name,
    )

    if no_builds:
        dependencies = ["=".join((a.name, a.version)) for a in conda_precs]
    else:
        dependencies = ["=".join((a.name, a.version, a.build)) for a in conda_precs]
    if pip_precs:
        dependencies.append({"pip": [f"{a.name}=={a.version}" for a in pip_precs]})

    channels = list(context.channels)
    if not ignore_channels:
        for prec in conda_precs:
            canonical_name = prec.channel.canonical_name
            if canonical_name not in channels:
                channels.insert(0, canonical_name)
    return Environment(
        name=name,
        dependencies=dependencies,
        channels=channels,
        prefix=prefix,
        variables=variables,
    )


def from_yaml(yamlstr, **kwargs):
    """Load and return a ``Environment`` from a given ``yaml`` string"""
    data = yaml_safe_load(yamlstr)
    filename = kwargs.get("filename")
    if data is None:
        raise EnvironmentFileEmpty(filename)
    data = validate_keys(data, kwargs)

    if kwargs is not None:
        for key, value in kwargs.items():
            data[key] = value
    _expand_channels(data)
    return Environment(**data)


def _expand_channels(data):
    """Expands ``Environment`` variables for the channels found in the ``yaml`` data"""
    data["channels"] = [
        os.path.expandvars(channel) for channel in data.get("channels", [])
    ]


def from_file(filename):
    """Load and return an ``Environment`` from a given file"""
    url_scheme = filename.split("://", 1)[0]
    if url_scheme in CONDA_SESSION_SCHEMES:
        yamlstr = download_text(filename)
    elif not os.path.exists(filename):
        raise EnvironmentFileNotFound(filename)
    else:
        with open(filename, "rb") as fp:
            yamlb = fp.read()
            try:
                yamlstr = yamlb.decode("utf-8")
            except UnicodeDecodeError:
                yamlstr = yamlb.decode("utf-16")
    return from_yaml(yamlstr, filename=filename)


class Dependencies(dict):
    """A ``dict`` subclass that parses the raw dependencies into a conda and pip list"""

    def __init__(self, raw, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raw = raw
        self.parse()

    def parse(self):
        """Parse the raw dependencies into a conda and pip list"""
        if not self.raw:
            return

        self.update({"conda": []})

        for line in self.raw:
            if isinstance(line, dict):
                self.update(line)
            else:
                self["conda"].append(common.arg2spec(line))

        if "pip" in self:
            if not self["pip"]:
                del self["pip"]
            if not any(MatchSpec(s).name == "pip" for s in self["conda"]):
                self["conda"].append("pip")

    # TODO only append when it's not already present
    def add(self, package_name):
        """Add a package to the ``Environment``"""
        self.raw.append(package_name)
        self.parse()


@total_ordering
class Requirement(ABC):
    """A single requirement for a package.

    Can either be a single spec string (e.g. "flask"), or a dictionary containing
    a conditionally present package, and a spec to include if that condition is present.
    For example:

    {
        "if": "__linux",    # <-- if __linux is present, also include flask as a requirement
        "then": "flask",
    }
    """

    def __init__(self, spec: str | dict[str, str]):
        if isinstance(spec, str):
            self.spec = spec
            self.condition = None
        elif isinstance(spec, dict):
            for key in ["if", "then"]:
                if key not in spec:
                    raise ValueError(f"Conditional requirement missing an `{key}` key.")

            self.spec = spec["then"]
            self.condition = spec["if"]
        else:
            raise ValueError(f"Invalid requirement: {spec}")

    def __repr__(self) -> str:
        result = self.spec
        if self.condition:
            result = f"{result} (if {self.condition})"
        return result

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Requirement):
            return self.spec == other.spec

        raise NotImplementedError

    def __lt__(self, other: Requirement) -> bool:
        return self.spec < other.spec

    def serialize(self) -> str | dict[str, str]:
        """Serialize the package requirement.

        Can be a conditional requirement of the form

        {
            "if": "__win",
            "then": "flask"
        }

        :return: Serialized Requirement
        """
        if self.condition:
            return {"if": self.condition, "then": self.spec}
        return self.spec

    def __str__(self) -> str:
        return repr(self)


class PypiRequirement(Requirement):
    pass


class CondaRequirement(Requirement):
    pass


StringConditionalRequirement = dict[str, str]
StringRequirements = Iterable[str | StringConditionalRequirement]


class EnvironmentConfig:
    """A class that contains configuration variables for an environment.

    These variables override user configuration, e.g. settings in .condarc.
    """

    def __init__(self, **options):
        self.options = options

    def __repr__(self) -> str:
        lines = []
        for key, value in self.options.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def serialize(self) -> dict[str, str]:
        """Serialize the environment configuration.

        Since this is a thin wrapper around a dictionary, just return the underlying
        dict.

        :return: A dict of primitives containing configuration options for the
            environment
        """
        return self.options


class EnvironmentBase:
    """A base class representing an ``environment.yaml`` file"""

    def to_dict(self) -> dict:
        raise NotImplementedError

    def to_yaml(self) -> str | None:
        raise NotImplementedError

    def save(self):
        raise NotImplementedError


class EnvironmentV2(EnvironmentBase):
    """A class representing a V2 environment.yaml."""

    def __init__(
        self,
        requirements: Iterable[Requirement] | None = None,
        groups: Mapping[str, Iterable[Requirement]] | None = None,
        name: str | None = None,
        config: EnvironmentConfig | None = None,
        **options,
    ):
        """Instantiate an EnvironmentV2.

        :param requirements: The packages contained in the environment
        :param groups: Groups of packages contained in the environment; these can
            represent optional dependencies, e.g. 'dev'
        :param name: Name of the environment
        :param config: Variables which override conda settings in `.condarc`
        :param options: Environment-specific options which are not configuration
            overrides, e.g. `description`
        """
        self.name = name
        self.requirements = requirements if requirements else []
        self.groups = groups if groups else {}
        self.options = options
        self.config = config if config else EnvironmentConfig()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnvironmentV2:
        """Create a new EnvironmentV2 instance from a dictionary.

        Shell variables in channels are automatically expanded.

        :param data: Serialized EnvironmentV2 object
        :return:  A new EnvironmentV2 instance
        """

        requirements = cls.parse_requirements(
            str_requirements_conda=data.pop("requirements"),
            str_requirements_pypi=data.pop("pypi-requirements"),
        )

        groups = {}
        for group in data.pop("groups", []):
            group_name: str = group["group"]
            groups[group_name] = cls.parse_requirements(
                str_requirements_conda=group.get("requirements"),
                str_requirements_pypi=group.get("pypi-requirements"),
            )

        return cls(
            name=data.pop("name", None),
            requirements=requirements,
            groups=groups,
            description=data.pop("description", None),
            config=EnvironmentConfig(
                channels=[os.path.expandvars(ch) for ch in data.pop("channels", [])],
                channel_priority=data.pop("channel-priority", None),
                repodata_fn=data.pop("repodata-fn", None),
                variables=data.pop("variables", {}),
                version=data.pop("version", 2),
            ),
        )

    @staticmethod
    def parse_requirements(
        str_requirements_conda: StringRequirements | None = None,
        str_requirements_pypi: StringRequirements | None = None,
    ) -> list[Requirement]:
        """Parse the string requirements for an environment.

        :param str_requirements_conda: A list of either strings representing conda requirements,
            e.g. 'foo=1.2.3', or dictionaries of conditional conda requirements, e.g.

            {
                "if": "__win",
                "then": "flask"
            }

        :param str_requirements_pypi: PyPI requirements for the environment; can include conditional
            requirements just like str_requirements_conda
        :return: A list of Requirement objects, one for each input requirement
        """
        if str_requirements_conda is None:
            str_requirements_conda = []

        if str_requirements_pypi is None:
            str_requirements_pypi = []

        requirements_conda: list[Requirement] = []
        for req in str_requirements_conda:
            requirements_conda.append(CondaRequirement(req))

        requirements_pypi: list[Requirement] = []
        for req in str_requirements_pypi:
            requirements_pypi.append(PypiRequirement(req))

        return [*requirements_conda, *requirements_pypi]

    @classmethod
    def from_file(cls, filename: os.PathLike[str]) -> EnvironmentV2:
        """Create a new EnvironmentV2 instance from a file.

        :param filename: Name of the file containing the v2 environment spec
        :return: A new EnvironmentV2 instance
        """
        with open(filename) as f:
            data = f.read()

        return EnvironmentV2.from_yaml(data)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> EnvironmentV2:
        """Create a new EnvironmentV2 instance from a yaml string.

        :param yaml_str: String of valid YAML containing the environment spec
        :return: A new EnvironmentV2 instance
        """
        return EnvironmentV2.from_dict(yaml_safe_load(yaml_str))

    def serialize(self) -> dict[str, Any]:
        """Convert the environment into a dict.

        :return: A dict representation of the environment
        """
        result: dict[str, Any] = {}
        result["name"] = self.name
        result["options"] = self.options
        result["config"] = self.config.serialize()
        result["requirements"] = [
            req.serialize()
            for req in self.requirements
            if isinstance(req, CondaRequirement)
        ]
        result["pypi-requirements"] = [
            req.serialize()
            for req in self.requirements
            if isinstance(req, PypiRequirement)
        ]

        groups = []
        for name, group in self.groups.items():
            group_dict: dict[str, str | Iterable[str | dict[str, str]]] = {
                "group": name,
            }

            group_reqs_conda = [
                req.serialize() for req in group if isinstance(req, CondaRequirement)
            ]
            if group_reqs_conda:
                group_dict["requirements"] = group_reqs_conda

            group_reqs_pypi = [
                req.serialize() for req in group if isinstance(req, PypiRequirement)
            ]
            if group_reqs_pypi:
                group_dict["pypi-requirements"] = group_reqs_pypi

            groups[name] = [req.serialize() for req in group]
        result["groups"] = groups

        return result

    def to_yaml(self, stream: io.TextIOBase | None = None) -> str | None:
        """Write the environment as yaml to ``stream``, or return it as a string.

        :param stream: Stream to write the yaml to
        :return: YAML string (if no stream specified), otherwise None
        """
        out = yaml_safe_dump(self.serialize(), stream)
        if stream is None:
            return out
        return None

    def to_file(self, filename: os.PathLike) -> None:
        """Serialize the environment and dump it to a file as yaml.

        :param filename: Name of the file to write the environment to
        """
        with open(filename, "w") as f:
            yaml_safe_dump(self.serialize(), stream=f)

    def __repr__(self) -> str:
        groups_lines = []
        for name, group in self.groups.items():
            groups_lines.append(f"{name}:")
            groups_lines.append(textwrap.indent(repr(group), "  "))

        lines = [
            f"name: {self.name if self.name else '<none>'}",
            "options:",
            textwrap.indent(
                "\n".join([f"{key}: {value}" for key, value in self.options.items()]),
                prefix="  ",
            ),
            "configuration:",
            textwrap.indent(repr(self.config), "  "),
            "requirements:",
            textwrap.indent(repr(self.requirements), "  "),
            "groups:",
            textwrap.indent(
                "\n".join(groups_lines),
                "  ",
            ),
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Return the environment as a dictionary.

        :return: The environment as a dictionary
        """
        return self.serialize()

    @classmethod
    def from_history(cls, prefix: os.PathLike) -> EnvironmentV2:
        """Create an Environment from the history of the requested packages in a prefix.

        :param prefix: Prefix of the target conda environment
        :return: EnvironmentV2 object containing all the user-requested conda packages
        """
        name = get_env_name(prefix)

        requirements = []
        for spec in History(prefix).get_requested_specs_map().values():
            requirements.append(str(spec))

        return EnvironmentV2.from_dict(
            {
                "name": name if name else None,
                "requirements": requirements,
                "variables": PrefixData(
                    prefix, pip_interop_enabled=True
                ).get_environment_env_vars(),
            }
        )

    @classmethod
    def from_prefix(cls, prefix: os.PathLike) -> EnvironmentV2:
        """Create an Environment from the prefix of an environment on disk.

        :param prefix: Prefix of the target conda environment
        :return: EnvironmentV2 object containing all the conda packages in the prefix
        """
        pfd = PrefixData(prefix, pip_interop_enabled=True)
        variables = pfd.get_environment_env_vars()

        precs = tuple(PrefixGraph(pfd.iter_records()).graph)

        conda_precs, pip_precs = [], []
        for prec in precs:
            if prec.package_type in [
                None,
                PackageType.NOARCH_GENERIC,
                PackageType.NOARCH_PYTHON,
            ]:
                conda_precs.append(prec)
            elif prec.package_type in [
                PackageType.VIRTUAL_PYTHON_WHEEL,
                PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE,
                PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE,
            ]:
                pip_precs.append(prec)

        requirements = ["=".join((a.name, a.version, a.build)) for a in conda_precs]
        pypi_requirements = [f"{a.name}=={a.version}" for a in pip_precs]

        channels = [prec.channel.canonical_name for prec in conda_precs]
        name = get_env_name(prefix)

        return cls(
            name=name if name else None,
            requirements=cls.parse_requirements(
                str_requirements_conda=requirements,
                str_requirements_pypi=pypi_requirements,
            ),
            config=EnvironmentConfig(
                channels=channels,
                variables=variables,
            ),
        )


class Environment(EnvironmentBase):
    """A class representing an ``environment.yaml`` file"""

    def __init__(
        self,
        name=None,
        filename=None,
        channels=None,
        dependencies=None,
        prefix=None,
        variables=None,
    ):
        self.name = name
        self.filename = filename
        self.prefix = prefix
        self.dependencies = Dependencies(dependencies)
        self.variables = variables

        if channels is None:
            channels = []
        self.channels = channels

    def add_channels(self, channels):
        """Add channels to the ``Environment``"""
        self.channels = list(unique(chain.from_iterable((channels, self.channels))))

    def remove_channels(self):
        """Remove all channels from the ``Environment``"""
        self.channels = []

    def to_dict(self, stream=None):
        """Convert information related to the ``Environment`` into a dictionary"""
        d = {"name": self.name}
        if self.channels:
            d["channels"] = self.channels
        if self.dependencies:
            d["dependencies"] = self.dependencies.raw
        if self.variables:
            d["variables"] = self.variables
        if self.prefix:
            d["prefix"] = self.prefix
        if stream is None:
            return d
        stream.write(json.dumps(d))

    def to_yaml(self, stream=None):
        """Convert information related to the ``Environment`` into a ``yaml`` string"""
        d = self.to_dict()
        out = yaml_safe_dump(d, stream)
        if stream is None:
            return out

    def save(self):
        """Save the ``Environment`` data to a ``yaml`` file"""
        with open(self.filename, "wb") as fp:
            self.to_yaml(stream=fp)


def get_filename(filename):
    """Expand filename if local path or return the ``url``"""
    url_scheme = filename.split("://", 1)[0]
    if url_scheme in CONDA_SESSION_SCHEMES:
        return filename
    else:
        return abspath(expanduser(expandvars(filename)))


def print_result(args, prefix, result):
    """Print the result of an install operation"""
    if context.json:
        if result["conda"] is None and result["pip"] is None:
            common.stdout_json_success(
                message="All requested packages already installed."
            )
        else:
            if result["conda"] is not None:
                actions = result["conda"]
            else:
                actions = {}
            if result["pip"] is not None:
                actions["PIP"] = result["pip"]
            common.stdout_json_success(prefix=prefix, actions=actions)
    else:
        install.print_activate(args.name or prefix)


def get_env_name(prefix: os.PathLike) -> str:
    """Get the name of the environment at the given prefix.

    :param prefix: Prefix for which the environment name should be retrieved
    :return: Name of the environment; if the prefix lives outside of
        ``context.envs_dirs``, it doesn't have a name. If it does, the name is
        the basename of the prefix. If the prefix matches ``context.root_prefix``,
        the name is ROOT_ENV_NAME.
    """
    if prefix == context.root_prefix:
        return ROOT_ENV_NAME

    for envs_dir in context.envs_dirs:
        if paths_equal(envs_dir, dirname(prefix)):
            return basename(prefix)

    return ""
