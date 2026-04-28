# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the conda._ng scaffolding and experimental=ng routing."""

from __future__ import annotations

import os
from argparse import Namespace
from unittest.mock import MagicMock, patch

from conda.base.context import context, reset_context

# ---------------------------------------------------------------------------
# conda.ng shim
# ---------------------------------------------------------------------------


class TestNgShim:
    """Tests for the conda.ng module-level entry-point shim."""

    def test_inject_ng_experimental_adds_ng_when_absent(self, monkeypatch):
        """_inject_ng_experimental sets CONDA_EXPERIMENTAL=ng when unset."""
        monkeypatch.delenv("CONDA_EXPERIMENTAL", raising=False)

        from conda.ng import _inject_ng_experimental

        _inject_ng_experimental()

        assert "ng" in os.environ["CONDA_EXPERIMENTAL"].split(",")

    def test_inject_ng_experimental_preserves_existing_values(self, monkeypatch):
        """_inject_ng_experimental keeps pre-existing experimental values."""
        monkeypatch.setenv("CONDA_EXPERIMENTAL", "some_other_flag")

        from conda.ng import _inject_ng_experimental

        _inject_ng_experimental()
        values = os.environ["CONDA_EXPERIMENTAL"].split(",")
        assert "ng" in values
        assert "some_other_flag" in values

    def test_inject_ng_experimental_idempotent(self, monkeypatch):
        """Calling _inject_ng_experimental twice must not duplicate 'ng'."""
        monkeypatch.delenv("CONDA_EXPERIMENTAL", raising=False)

        from conda.ng import _inject_ng_experimental

        _inject_ng_experimental()
        _inject_ng_experimental()
        values = os.environ["CONDA_EXPERIMENTAL"].split(",")
        assert values.count("ng") == 1

    def test_ng_module_is_importable(self):
        """conda.ng must be importable without side-effects."""
        import conda.ng  # noqa: F401 — should not raise

    def test_ng_module_callable_as_main(self, monkeypatch):
        """conda.ng.main() must delegate to conda.cli.main.main."""
        monkeypatch.delenv("CONDA_EXPERIMENTAL", raising=False)

        called_with = []

        def fake_main(*args, **kwargs):
            called_with.append((args, kwargs))
            return 0

        with patch("conda.cli.main.main", fake_main):
            from conda.ng import main as ng_main

            result = ng_main()

        assert result == 0
        assert called_with, "conda.cli.main.main was not called"

    def test_python_m_conda_ng_sets_ng_flag_on_context(self, monkeypatch):
        """python -m conda.ng ensures context.experimental contains 'ng'."""
        monkeypatch.delenv("CONDA_EXPERIMENTAL", raising=False)

        def fake_main(*args, **kwargs):
            # After the shim injects the env var, reset_context() is called
            # inside the real main(); here we simulate that and verify the
            # context object sees the 'ng' flag.
            reset_context()
            assert "ng" in context.experimental, (
                "context.experimental did not contain 'ng' after shim injection"
            )
            return 0

        with patch("conda.cli.main.main", fake_main):
            from conda.ng import main as ng_main

            ng_main()


# ---------------------------------------------------------------------------
# do_call routing
# ---------------------------------------------------------------------------


class TestDoCallNgRouting:
    """Tests that do_call() routes create/install to conda._ng when experimental=ng."""

    def _make_args(self, command: str) -> Namespace:
        """Build a minimal Namespace that do_call() can work with."""
        func = f"conda.cli.main_{command}.execute"
        return Namespace(func=func, cmd=command)

    def test_install_routes_to_ng_when_flag_set(self, monkeypatch):
        """do_call routes 'install' to conda._ng.cli.main_install when ng is active."""
        monkeypatch.setenv("CONDA_EXPERIMENTAL", "ng")
        reset_context()
        assert "ng" in context.experimental

        ng_execute = MagicMock(return_value=0)
        pm = MagicMock()
        pm.invoke_pre_commands = MagicMock()
        pm.invoke_post_commands = MagicMock()
        with (
            patch("conda._ng.cli.main_install.execute", ng_execute),
            patch("conda.plugins.manager.get_plugin_manager", return_value=pm),
        ):
            from conda.cli.conda_argparse import do_call, generate_parser

            parser = generate_parser()
            args = self._make_args("install")
            do_call(args, parser)

        ng_execute.assert_called_once()

    def test_create_routes_to_ng_when_flag_set(self, monkeypatch):
        """do_call routes 'create' to conda._ng.cli.main_create when ng is active."""
        monkeypatch.setenv("CONDA_EXPERIMENTAL", "ng")
        reset_context()
        assert "ng" in context.experimental

        ng_execute = MagicMock(return_value=0)
        pm = MagicMock()
        pm.invoke_pre_commands = MagicMock()
        pm.invoke_post_commands = MagicMock()
        with (
            patch("conda._ng.cli.main_create.execute", ng_execute),
            patch("conda.plugins.manager.get_plugin_manager", return_value=pm),
        ):
            from conda.cli.conda_argparse import do_call, generate_parser

            parser = generate_parser()
            args = self._make_args("create")
            do_call(args, parser)

        ng_execute.assert_called_once()

    def test_install_uses_classic_without_ng_flag(self, monkeypatch):
        """do_call routes 'install' to the classic module when ng flag is absent."""
        monkeypatch.delenv("CONDA_EXPERIMENTAL", raising=False)
        reset_context()
        assert "ng" not in context.experimental

        classic_execute = MagicMock(return_value=0)
        pm = MagicMock()
        pm.invoke_pre_commands = MagicMock()
        pm.invoke_post_commands = MagicMock()
        with (
            patch("conda.cli.main_install.execute", classic_execute),
            patch("conda.plugins.manager.get_plugin_manager", return_value=pm),
        ):
            from conda.cli.conda_argparse import do_call, generate_parser

            parser = generate_parser()
            args = self._make_args("install")
            do_call(args, parser)

        classic_execute.assert_called_once()

    def test_non_routed_command_unaffected_by_ng_flag(self, monkeypatch):
        """do_call does NOT redirect 'search' even when ng is active."""
        monkeypatch.setenv("CONDA_EXPERIMENTAL", "ng")
        reset_context()
        assert "ng" in context.experimental

        classic_execute = MagicMock(return_value=0)
        pm = MagicMock()
        pm.invoke_pre_commands = MagicMock()
        pm.invoke_post_commands = MagicMock()
        with (
            patch("conda.cli.main_search.execute", classic_execute),
            patch("conda.plugins.manager.get_plugin_manager", return_value=pm),
        ):
            from conda.cli.conda_argparse import do_call, generate_parser

            parser = generate_parser()
            args = self._make_args("search")
            do_call(args, parser)

        classic_execute.assert_called_once()


# ---------------------------------------------------------------------------
# conda._ng package smoke tests
# ---------------------------------------------------------------------------


class TestNgPackageLayout:
    """Verify the basic package layout exists and is importable."""

    def test_ng_package_importable(self):
        import conda._ng  # noqa: F401

    def test_ng_cli_package_importable(self):
        import conda._ng.cli  # noqa: F401

    def test_ng_cli_main_install_importable(self):
        import conda._ng.cli.main_install  # noqa: F401

    def test_ng_cli_main_create_importable(self):
        import conda._ng.cli.main_create  # noqa: F401

    def test_ng_cli_main_install_has_execute(self):
        from conda._ng.cli.main_install import execute

        assert callable(execute)

    def test_ng_cli_main_create_has_execute(self):
        from conda._ng.cli.main_create import execute

        assert callable(execute)
