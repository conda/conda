# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the conda._ng scaffolding and experimental=ng routing."""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import MagicMock, patch

from conda.base.context import context, reset_context

# ---------------------------------------------------------------------------
# conda.ng shim
# ---------------------------------------------------------------------------


class TestNgShim:
    """Tests for the conda.ng module-level entry-point shim."""

    def test_inject_ng_experimental_adds_ng_when_absent(self):
        """_inject_ng_experimental sets context.experimental to include 'ng' when absent."""
        reset_context()
        assert "ng" not in context.experimental

        from conda.ng import _inject_ng_experimental

        with _inject_ng_experimental():
            assert "ng" in context.experimental

        # context is restored on exit
        assert "ng" not in context.experimental

    def test_inject_ng_experimental_preserves_existing_values(self):
        """_inject_ng_experimental keeps pre-existing experimental values."""
        context.__init__(argparse_args=Namespace(experimental=["some_other_flag"]))
        assert "some_other_flag" in context.experimental

        from conda.ng import _inject_ng_experimental

        with _inject_ng_experimental():
            assert "ng" in context.experimental
            assert "some_other_flag" in context.experimental

        # "ng" is gone, "some_other_flag" is restored
        assert "ng" not in context.experimental
        assert "some_other_flag" in context.experimental

        reset_context()

    def test_inject_ng_experimental_idempotent(self):
        """Entering _inject_ng_experimental twice must not duplicate 'ng'."""
        reset_context()

        from conda.ng import _inject_ng_experimental

        with _inject_ng_experimental():
            with _inject_ng_experimental():
                assert context.experimental.count("ng") == 1

        reset_context()

    def test_ng_module_is_importable(self):
        """conda.ng must be importable without side-effects."""
        import conda.ng  # noqa: F401 — should not raise

    def test_ng_module_callable_as_main(self):
        """conda.ng.main() must delegate to conda.cli.main.main."""
        import sys

        _cli_main_module = sys.modules["conda.cli.main"]
        called_with = []

        def fake_main(*args, **kwargs):
            called_with.append((args, kwargs))
            return 0

        with patch.object(_cli_main_module, "main", fake_main):
            from conda.ng import main as ng_main

            result = ng_main()

        assert result == 0
        assert called_with, "conda.cli.main.main was not called"

    def test_python_m_conda_ng_sets_ng_flag_on_context(self):
        """python -m conda.ng ensures context.experimental contains 'ng'."""
        import sys

        _cli_main_module = sys.modules["conda.cli.main"]
        reset_context()

        def fake_main(*args, **kwargs):
            # The shim has already injected "ng" into context before delegating
            # to main(); verify the context object sees the 'ng' flag.
            assert "ng" in context.experimental, (
                "context.experimental did not contain 'ng' after shim injection"
            )
            return 0

        with patch.object(_cli_main_module, "main", fake_main):
            from conda.ng import main as ng_main

            ng_main()

        # After main() returns the context manager restores the original state
        assert "ng" not in context.experimental

        reset_context()


# ---------------------------------------------------------------------------
# do_call routing
# ---------------------------------------------------------------------------


class TestDoCallNgRouting:
    """Tests that do_call() routes create/install to conda._ng when experimental=ng."""

    def _make_args(self, command: str) -> Namespace:
        """Build a minimal Namespace that do_call() can work with."""
        func = f"conda.cli.main_{command}.execute"
        return Namespace(func=func, cmd=command)

    def test_install_routes_to_ng_when_flag_set(self):
        """do_call routes 'install' to conda._ng.cli.main_install when ng is active."""
        context.__init__(argparse_args=Namespace(experimental=["ng"]))
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
        reset_context()

    def test_create_routes_to_ng_when_flag_set(self):
        """do_call routes 'create' to conda._ng.cli.main_create when ng is active."""
        context.__init__(argparse_args=Namespace(experimental=["ng"]))
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
        reset_context()

    def test_install_uses_classic_without_ng_flag(self):
        """do_call routes 'install' to the classic module when ng flag is absent."""
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

    def test_non_routed_command_unaffected_by_ng_flag(self):
        """do_call does NOT redirect 'search' even when ng is active."""
        context.__init__(argparse_args=Namespace(experimental=["ng"]))
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
        reset_context()


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
