# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import importlib
import re
from inspect import isclass, isfunction
from logging import getLogger
from typing import Any, Callable

import pytest

from conda.cli.conda_argparse import generate_parser
from conda.exceptions import EnvironmentLocationNotFound
from conda.testing import CondaCLIFixture

log = getLogger(__name__)


def test_list_through_python_api(conda_cli: CondaCLIFixture):
    with pytest.raises(EnvironmentLocationNotFound, match="Not a conda environment"):
        conda_cli("list", "--prefix", "not-a-real-path")

    # cover argument variations
    # mutually exclusive: --canonical, --export, --explicit, (default human readable)
    for args1 in [[], ["--json"]]:
        for args2 in [[], ["--revisions"]]:
            for args3 in [
                ["--canonical"],
                ["--export"],
                ["--explicit", "--md5"],
                ["--full-name"],
            ]:
                args = (*args1, *args2, *args3)
                stdout, _, _ = conda_cli("list", *args)
                if "--md5" in args and "--revisions" not in args:
                    assert re.search(r"#[0-9a-f]{32}", stdout)


def test_parser_basics():
    p = generate_parser()
    with pytest.raises(SystemExit, match="2"):
        p.parse_args(["blarg", "--flag"])

    args = p.parse_args(["install", "-vv"])
    assert args.verbosity == 2


def test_cli_args_as_strings(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli("config", "--show", "add_anaconda_token")
    assert stdout
    assert not stderr
    assert not err


@pytest.mark.parametrize(
    "path,validate",
    [
        ("conda.cli.conda_argparse.add_output_and_prompt_options", isfunction),
        ("conda.cli.conda_argparse.add_parser_channels", isfunction),
        ("conda.cli.conda_argparse.add_parser_create_install_update", isfunction),
        ("conda.cli.conda_argparse.add_parser_default_packages", isfunction),
        ("conda.cli.conda_argparse.add_parser_help", isfunction),
        ("conda.cli.conda_argparse.add_parser_json", isfunction),
        ("conda.cli.conda_argparse.add_parser_known", isfunction),
        ("conda.cli.conda_argparse.add_parser_networking", isfunction),
        ("conda.cli.conda_argparse.add_parser_package_install_options", isfunction),
        ("conda.cli.conda_argparse.add_parser_prefix", isfunction),
        ("conda.cli.conda_argparse.add_parser_prune", isfunction),
        ("conda.cli.conda_argparse.add_parser_pscheck", isfunction),
        ("conda.cli.conda_argparse.add_parser_show_channel_urls", isfunction),
        ("conda.cli.conda_argparse.add_parser_solver", isfunction),
        ("conda.cli.conda_argparse.add_parser_solver_mode", isfunction),
        ("conda.cli.conda_argparse.add_parser_update_modifiers", isfunction),
        ("conda.cli.conda_argparse.add_parser_verbose", isfunction),
        # derived from argparse.ArgumentParser
        ("conda.cli.conda_argparse.ArgumentParser", isclass),
        ("conda.cli.conda_argparse.BUILTIN_COMMANDS", lambda x: isinstance(x, set)),
        ("conda.cli.conda_argparse.configure_parser_clean", isfunction),
        ("conda.cli.conda_argparse.configure_parser_compare", isfunction),
        ("conda.cli.conda_argparse.configure_parser_config", isfunction),
        ("conda.cli.conda_argparse.configure_parser_create", isfunction),
        ("conda.cli.conda_argparse.configure_parser_info", isfunction),
        ("conda.cli.conda_argparse.configure_parser_init", isfunction),
        ("conda.cli.conda_argparse.configure_parser_install", isfunction),
        ("conda.cli.conda_argparse.configure_parser_list", isfunction),
        ("conda.cli.conda_argparse.configure_parser_notices", isfunction),
        ("conda.cli.conda_argparse.configure_parser_package", isfunction),
        ("conda.cli.conda_argparse.configure_parser_plugins", isfunction),
        ("conda.cli.conda_argparse.configure_parser_remove", isfunction),
        ("conda.cli.conda_argparse.configure_parser_rename", isfunction),
        ("conda.cli.conda_argparse.configure_parser_run", isfunction),
        ("conda.cli.conda_argparse.configure_parser_search", isfunction),
        ("conda.cli.conda_argparse.configure_parser_update", isfunction),
        ("conda.cli.conda_argparse.do_call", isfunction),
        ("conda.cli.conda_argparse.escaped_sys_rc_path", lambda x: isinstance(x, str)),
        ("conda.cli.conda_argparse.escaped_user_rc_path", lambda x: isinstance(x, str)),
        ("conda.cli.conda_argparse.ExtendConstAction", isclass),
        ("conda.cli.conda_argparse.find_builtin_commands", isfunction),
        ("conda.cli.conda_argparse.generate_parser", isfunction),
        ("conda.cli.conda_argparse.generate_pre_parser", isfunction),
        ("conda.cli.conda_argparse.NullCountAction", isclass),
        ("conda.cli.conda_argparse.sys_rc_path", lambda x: isinstance(x, str)),
        ("conda.cli.conda_argparse.user_rc_path", lambda x: isinstance(x, str)),
    ],
)
def test_imports(path: str, validate: Callable[[Any], bool]):
    path, attr = path.rsplit(".", 1)
    module = importlib.import_module(path)
    assert hasattr(module, attr)
    assert validate(getattr(module, attr))
