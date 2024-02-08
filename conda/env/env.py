# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Environment object describing the conda environment.yaml file."""
import json
import os
import re
from itertools import chain
from os.path import abspath, expanduser, expandvars

from ..cli import common
from ..common.iterators import unique
from ..common.serialize import yaml_safe_dump, yaml_safe_load
from ..exceptions import EnvironmentFileEmpty, EnvironmentFileNotFound
from ..gateways.connection.download import download_text
from ..gateways.connection.session import CONDA_SESSION_SCHEMES
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


class Environment:
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
    from ..base.context import context
    from ..cli import install
    from ..cli.common import stdout_json_success

    """Print the result of an install operation"""
    if context.json:
        if result["conda"] is None and result["pip"] is None:
            stdout_json_success(message="All requested packages already installed.")
        else:
            if result["conda"] is not None:
                actions = result["conda"]
            else:
                actions = {}
            if result["pip"] is not None:
                actions["PIP"] = result["pip"]
            stdout_json_success(prefix=prefix, actions=actions)
    else:
        install.print_activate(args.name or prefix)
