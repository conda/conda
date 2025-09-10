# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Environment object describing the conda environment.yaml file."""

import os
import re
from itertools import chain

from ..base.context import context
from ..cli import common
from ..common.iterators import unique
from ..common.path import expand
from ..common.serialize import json, yaml_safe_dump, yaml_safe_load
from ..core.prefix_data import PrefixData
from ..deprecations import deprecated
from ..exceptions import EnvironmentFileEmpty, EnvironmentFileNotFound
from ..gateways.connection.download import download_text
from ..gateways.connection.session import CONDA_SESSION_SCHEMES
from ..history import History
from ..models.environment import Environment as EnvironmentModel
from ..models.environment import EnvironmentConfig
from ..models.match_spec import MatchSpec

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
        Get ``EnvironmentYaml`` object from prefix
    Args:
        name: The name of environment
        prefix: The path of prefix
        no_builds: Whether has build requirement
        ignore_channels: whether ignore_channels
        from_history: Whether environment file should be based on explicit specs in history

    Returns:     EnvironmentYaml object
    """
    pd = PrefixData(prefix, interoperability=True)
    variables = pd.get_environment_env_vars()

    if from_history:
        history = History(prefix).get_requested_specs_map()
        deps = [str(package) for package in history.values()]
        return EnvironmentYaml(
            name=name,
            dependencies=deps,
            channels=list(context.channels),
            prefix=prefix,
            variables=variables,
        )

    conda_precs = pd.get_conda_packages()
    python_precs = pd.get_python_packages()

    dependencies = [
        conda_prec.spec_no_build if no_builds else conda_prec.spec
        for conda_prec in conda_precs
    ]
    if python_precs:
        dependencies.append(
            {
                "pip": [
                    f"{python_prec.name}=={python_prec.version}"
                    for python_prec in python_precs
                ]
            }
        )

    channels = list(context.channels)
    if not ignore_channels:
        for conda_prec in conda_precs:
            canonical_name = conda_prec.channel.canonical_name
            if canonical_name not in channels:
                channels.insert(0, canonical_name)

    return EnvironmentYaml(
        name=name,
        dependencies=dependencies,
        channels=channels,
        prefix=prefix,
        variables=variables,
    )


def from_yaml(yamlstr, **kwargs):
    """Load and return a ``EnvironmentYaml`` from a given ``yaml`` string"""
    data = yaml_safe_load(yamlstr)
    filename = kwargs.get("filename")
    if data is None:
        raise EnvironmentFileEmpty(filename)
    data = validate_keys(data, kwargs)

    if kwargs is not None:
        for key, value in kwargs.items():
            data[key] = value
    _expand_channels(data)
    return EnvironmentYaml(**data)


def _expand_channels(data):
    """Expands ``EnvironmentYaml`` variables for the channels found in the ``yaml`` data"""
    data["channels"] = [
        os.path.expandvars(channel) for channel in data.get("channels", [])
    ]


def from_file(filename):
    """Load and return an ``EnvironmentYaml`` from a given file"""
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
                self["conda"].append(str(MatchSpec(line)))

        if "pip" in self:
            if not self["pip"]:
                del self["pip"]
            if not any(MatchSpec(s).name == "pip" for s in self["conda"]):
                self["conda"].append("pip")

    # TODO only append when it's not already present
    def add(self, package_name):
        """Add a package to the ``EnvironmentYaml``"""
        self.raw.append(package_name)
        self.parse()


class EnvironmentYaml:
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
        """Add channels to the ``EnvironmentYaml``"""
        self.channels = list(unique(chain.from_iterable((channels, self.channels))))

    def remove_channels(self):
        """Remove all channels from the ``EnvironmentYaml``"""
        self.channels = []

    def to_dict(self, stream=None):
        """Convert information related to the ``EnvironmentYaml`` into a dictionary"""
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
        """Convert information related to the ``EnvironmentYaml`` into a ``yaml`` string"""
        d = self.to_dict()
        out = yaml_safe_dump(d, stream)
        if stream is None:
            return out

    def save(self):
        """Save the ``EnvironmentYaml`` data to a ``yaml`` file"""
        with open(self.filename, "wb") as fp:
            self.to_yaml(stream=fp)

    def to_environment_model(self) -> EnvironmentModel:
        """Convert the ``Environment`` into a ``model.Environment`` object"""
        config = EnvironmentConfig(channels=tuple(self.channels))

        external_packages = {}
        if pip_dependencies := self.dependencies.get("pip"):
            external_packages["pip"] = pip_dependencies

        requested_packages = [
            MatchSpec(spec) for spec in self.dependencies.get("conda", [])
        ]

        return EnvironmentModel(
            prefix=self.prefix or context.target_prefix,
            platform=context.subdir,
            name=self.name,
            config=config,
            variables=self.variables,
            external_packages=external_packages,
            requested_packages=requested_packages,
        )


@deprecated("26.3", "26.9", addendum="Use `conda.env.env.EnvironmentYaml` instead.")
class Environment(EnvironmentYaml):
    """A class representing an ``environment.yaml`` file"""


@deprecated("25.9", "26.3")
def get_filename(filename):
    """Expand filename if local path or return the ``url``"""
    url_scheme = filename.split("://", 1)[0]
    if url_scheme in CONDA_SESSION_SCHEMES:
        return filename
    else:
        return expand(filename)


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
        common.print_activate(args.name or prefix)
