# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import sys
from pathlib import Path

from conda.env import env
from conda.env.specs.pyproject import PyProjectSpec

toml_dir = Path(__file__).parent.parent / "support/example-pyproject"
yaml_dir = toml_dir.with_name("example")


def test_only_simple_environment_table():
    toml_file = toml_dir / "demo-simple.toml"
    spec = PyProjectSpec(filename=toml_file)
    # Python<3.11 not supported as doesn't ship tomllib
    if not sys.version_info >= (3, 11):
        assert spec.environment is None
    else:
        assert isinstance(spec.environment, env.Environment)
        assert spec.environment.name == "demo"
        assert spec.environment.dependencies == {
            "conda": ["pytorch", "pytorch-cuda", "torchaudio", "torchvision", "pip"],
            "pip": ["requests"],
        }


def convert_environment_examples():
    """Automatically convert all the YAML examples to TOML for the test below.

    Shouldn't be necessary to ever run this unless extra examples are added or the
    current ones are changed, but it's left here just in case."""
    import tomli_w
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")

    toml_dir = Path(__file__).parent
    yaml_dir = Path(__file__).parent.parent / "example"

    for y in yaml_dir.iterdir():
        env = yaml.load(y)
        toml = {"tool": {"conda": {"environment": env}}}
        dest = (toml_dir / y.name).with_suffix(".toml")
        with open(dest, "wb") as f:
            tomli_w.dump(toml, f)


def test_environment_examples_equivalence():
    yaml_examples = [
        "environment_host_port.yml",
        "environment_pinned.yml",
        "environment.yml",
        "environment_pinned_updated.yml",
        "environment_with_pip.yml",
    ]
    for example in yaml_examples:
        print(f"Testing {example}")
        yaml_file = yaml_dir / example
        toml_file = (toml_dir / example).with_suffix(".toml")
        yaml_env = env.from_file(str(yaml_file))
        spec = PyProjectSpec(filename=toml_file)
        # Python<3.11 not supported as doesn't ship tomllib
        if not sys.version_info >= (3, 11):
            assert spec.environment is None
        else:
            toml_env = spec.environment
            assert yaml_env.name == toml_env.name
            assert yaml_env.channels == toml_env.channels
            assert yaml_env.dependencies == toml_env.dependencies
