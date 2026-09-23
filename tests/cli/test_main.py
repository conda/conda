# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.context import context
from conda.cli.main import main, main_sourced, main_subshell
from conda.common.compat import on_win
from conda.exceptions import PluginError

if TYPE_CHECKING:
    from pytest import CaptureFixture

    from conda.testing.fixtures import CondaCLIFixture


def test_main():
    with pytest.raises(SystemExit):
        __import__("conda.__main__")


@pytest.mark.parametrize("option", ("--trace", "-v", "--debug", "--json"))
def test_ensure_no_command_provided_returns_help(
    conda_cli: CondaCLIFixture, capsys, option
):
    """
    Regression test to make sure that invoking with just any of the options listed as parameters
    will not return a traceback.
    """
    with pytest.raises(SystemExit):
        conda_cli(option)

    captured = capsys.readouterr()

    assert "error: the following arguments are required: COMMAND" in captured.err


def test_main_subshell_help_exits_cleanly(capsys) -> None:
    """main_subshell("--help") should exit with SystemExit and print usage."""
    with pytest.raises(SystemExit) as exc_info:
        main_subshell("--help")

    stdout, stderr = capsys.readouterr()
    rc = exc_info.value.code

    assert rc == 0, f"main_subshell failed ({rc}): {stderr}"
    assert "usage" in stdout.lower()


def test_main_subshell_no_plugins_flag(monkeypatch) -> None:
    """CONDA_NO_PLUGINS=true should disable external plugins via main_subshell."""
    monkeypatch.setenv("CONDA_NO_PLUGINS", "true")
    disabled = []
    monkeypatch.setattr(
        context.plugin_manager,
        "disable_external_plugins",
        lambda **kwargs: disabled.append(True),
    )

    with pytest.raises(SystemExit):
        main_subshell("--help")

    assert context.no_plugins is True
    assert disabled


def test_main_subshell_no_plugins_names(monkeypatch) -> None:
    """--no-plugins=<names> disables the named plugins."""
    disabled = []
    monkeypatch.setattr(
        context.plugin_manager,
        "disable_plugins",
        lambda names, **kwargs: disabled.extend(names),
    )

    with pytest.raises(SystemExit):
        main_subshell("--no-plugins=plugin-a, plugin-b", "--help")

    assert disabled == ["plugin-a", "plugin-b"]


@pytest.mark.parametrize("option", ("--no-plugins", "--no-plugins="))
def test_main_subshell_no_plugins_option(monkeypatch, option: str) -> None:
    """--no-plugins disables all external plugins."""
    disabled = []
    monkeypatch.setattr(
        context.plugin_manager,
        "disable_external_plugins",
        lambda **kwargs: disabled.append(True),
    )

    assert main_subshell(option, "commands") == 0

    assert context.no_plugins is True
    assert disabled


@pytest.mark.parametrize(
    "name", ("conda-test-plugin", "Conda_Test.Plugin", "success", "test_plugin.success")
)
@pytest.mark.parametrize(
    "options,no_plugins,other_active",
    [
        ([], "false", True),
        (["--no-plugins"], "false", False),
        (["--no-plugins="], "false", False),
        ([], "true", False),
        (["--no-plugins=conda-test-plugin,other.plugin"], "false", False),
    ],
)
@pytest.mark.parametrize("enable_first", (False, True))
def test_main_subshell_enabled_plugins(
    plugin_manager, monkeypatch, name, options, no_plugins, other_active, enable_first
):
    monkeypatch.setenv("CONDA_NO_PLUGINS", no_plugins)
    assert plugin_manager.load_entrypoints("test_plugin", "success") == 1
    solver = plugin_manager.get_solver_backend("test")
    other = object()
    builtin = object()
    plugin_manager.register(other, "other.plugin")
    plugin_manager.register(builtin, "conda.plugins.test_builtin")
    enabled = ["--plugins", name]
    args = [*enabled, *options] if enable_first else [*options, *enabled]

    def check_args(parsed_args, parser):
        assert parsed_args.enabled_plugins == [name]

    assert main_subshell(*args, "commands", post_parse_hook=check_args) == 0

    assert plugin_manager.get_solver_backend("test") is solver
    assert plugin_manager.has_plugin("other.plugin") is other_active
    assert plugin_manager.get_plugin("conda.plugins.test_builtin") is builtin


@pytest.mark.parametrize("name", ("does-not-exist", "importerror", "", "success,"))
def test_main_subshell_enabled_plugin_unavailable(plugin_manager, name):
    assert plugin_manager.load_entrypoints("test_plugin", "success") == 1
    # A failed entry-point import must not count as an enabled plugin.
    assert plugin_manager.load_entrypoints("test_plugin", "importerror") == 0

    with pytest.raises(PluginError, match="No registered plugin matching"):
        main_subshell("--no-plugins", f"--plugins={name}", "commands")

    assert plugin_manager.has_plugin("test_plugin.success")


def test_main_subshell_enabled_plugin_multiple_modules(plugin_manager):
    assert plugin_manager.load_entrypoints("test_plugin", "success") == 1
    plugin_manager.register(object(), "second.plugin")
    plugin_manager.register(object(), "unrelated.plugin")
    plugin_manager.plugin_aliases["multi-plugin"] = {
        "test_plugin.success",
        "second.plugin",
    }

    assert main_subshell("--no-plugins", "--plugins=multi-plugin", "commands") == 0

    assert plugin_manager.has_plugin("test_plugin.success")
    assert plugin_manager.has_plugin("second.plugin")
    assert not plugin_manager.has_plugin("unrelated.plugin")


@pytest.mark.skipif(not on_win, reason="Windows-specific test")
@pytest.mark.parametrize(
    "shell,expected_patterns",
    [
        ("zsh", ["export"]),
        ("bash", ["export"]),
        ("posix", ["export"]),
        ("ash", ["export"]),
        ("dash", ["export"]),
        ("csh", ["setenv", "unsetenv"]),
        ("tcsh", ["setenv", "unsetenv"]),
        ("fish", ["set -gx", "set -e"]),
    ],
)
def test_main_sourced_shell_line_endings_fix_needed(
    shell: str, expected_patterns: list[str], capsys
) -> None:
    """Test that shells that need line ending fixes get appropriate treatment on Windows."""
    assert main_sourced(shell, "hook") == 0
    output = capsys.readouterr().out

    assert "\r" not in output
    assert any(pattern in output for pattern in expected_patterns)


@pytest.mark.skipif(not on_win, reason="Windows-specific test")
@pytest.mark.parametrize(
    "shell,expected_patterns",
    [
        ("cmd.exe", ["conda activate"]),
        ("powershell", ["$Env:", "Import-Module"]),
        ("xonsh", ["source-cmd", "source-bash"]),
    ],
)
def test_main_sourced_shell_line_endings_no_fix_needed(
    shell: str, expected_patterns: list[str], capsys
) -> None:
    """Test that shells that don't need line ending fixes work correctly on Windows."""
    assert main_sourced(shell, "hook") == 0
    output = capsys.readouterr().out

    assert any(pattern in output for pattern in expected_patterns)


@pytest.mark.skipif(on_win, reason="Unix-specific test")
@pytest.mark.parametrize(
    "shell,expected_patterns",
    [
        ("bash", ["export"]),
        ("zsh", ["export"]),
        ("fish", ["set -gx", "set -e"]),
        ("csh", ["setenv", "unsetenv"]),
        ("tcsh", ["setenv", "unsetenv"]),
        ("xonsh", ["source-bash"]),
    ],
)
def test_main_sourced_unix_shells_no_line_ending_fix(
    shell: str, expected_patterns: list[str], capsys
) -> None:
    """Test that Unix shells work correctly without line ending fixes."""
    assert main_sourced(shell, "hook") == 0
    output = capsys.readouterr().out

    assert any(pattern in output for pattern in expected_patterns)


@pytest.mark.parametrize("flag", ["-V", "--version"])
def test_version_fast_path(flag: str, capsys: CaptureFixture[str]) -> None:
    """``conda -V`` and ``conda --version`` use the fast path in main()."""
    from conda import __version__

    rc = main(flag)
    stdout, stderr = capsys.readouterr()

    assert rc == 0, f"conda {flag} failed ({rc}): {stderr}"
    assert stdout.strip() == f"conda {__version__}"


@pytest.mark.parametrize("flag", ["-V", "--version"])
def test_version_fast_path_skips_plugins(
    flag: str,
    clear_plugin_manager_cache: None,
) -> None:
    """The fast path must not trigger plugin loading."""
    from conda.plugins.manager import get_plugin_manager

    main(flag)
    assert get_plugin_manager.cache_info().currsize == 0
