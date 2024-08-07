# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from contextlib import contextmanager, nullcontext
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from conda.plugins import CondaReporterBackend, CondaReporterOutput
from conda.plugins.types import ProgressBarBase, ReporterRendererBase
from conda.reporters import (
    ProgressBarManager,
    get_progress_bar_context_managers,
    get_progress_bar_manager,
    render,
)

if TYPE_CHECKING:
    from typing import Callable, ContextManager

    from pytest import CaptureFixture


class DummyProgressbar(ProgressBarBase):
    """Dummy progress bar that does nothing"""

    def update_to(self, fraction) -> None:
        pass

    def refresh(self) -> None:
        pass

    def close(self) -> None:
        pass


class DummyReporterRenderer(ReporterRendererBase):
    def envs_list(self, data, **kwargs) -> str:
        return f"envs_list: {data}"

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return f"detail_view: {data}"

    def progress_bar(
        self,
        description: str,
        io_context_manager: Callable[[], ContextManager],
        **kwargs,
    ) -> ProgressBarBase:
        return DummyProgressbar(
            description="Dummy progress bar", io_context_manager=io_context_manager
        )


@contextmanager
def dummy_io():
    yield sys.stdout


@pytest.fixture
def reporters_setup(mocker):
    """Setup all mocks need for reporters tests"""
    reporter_backend = CondaReporterBackend(
        name="test-reporter-backend",
        description="test",
        renderer=DummyReporterRenderer,
    )
    reporter_output = CondaReporterOutput(
        name="test-reporter-output", description="test", stream=dummy_io
    )
    plugin_manager = SimpleNamespace(
        get_reporter_backend=lambda _: reporter_backend,
        get_reporter_output=lambda _: reporter_output,
    )
    reporters = (
        {"backend": "test-reporter-backend", "stream": "test-reporter-output"},
    )

    context = mocker.patch("conda.reporters.context")
    context.plugin_manager = plugin_manager
    context.reporters = reporters


def test_render(capsys: CaptureFixture, reporters_setup):
    """
    Ensure basic coverage of the :func:`~conda.reporters.render` function.
    """
    # Test simple rendering of object
    render("test-string")

    stdout, stderr = capsys.readouterr()
    assert stdout == "test-string"
    assert not stderr

    # Test rendering of object with a style
    render("test-string", style="envs_list")

    stdout, stderr = capsys.readouterr()
    assert stdout == "envs_list: test-string"
    assert not stderr

    # Test error when style cannot be found
    with pytest.raises(
        AttributeError,
        match="'non_existent_view' is not a valid reporter backend style",
    ):
        render({"test": "data"}, style="non_existent_view")


def test_get_progress_bar_manager(reporters_setup):
    """
    Ensure basic coverage of the :func:`~conda.reporters.get_progress_bar_manager~` function
    """
    progress_bar_manager = get_progress_bar_manager("test")

    assert isinstance(progress_bar_manager, ProgressBarManager)

    assert len(progress_bar_manager._progress_bars) == 1
    assert isinstance(progress_bar_manager._progress_bars[0], DummyProgressbar)


def test_get_progress_bar_context_managers(reporters_setup):
    """
    Ensure basic coverage of the
    :func:`~conda.reporters.get_progress_bar_context_managers~` function
    """
    progress_bar_context_managers = get_progress_bar_context_managers()

    assert len(progress_bar_context_managers) == 1
    assert isinstance(progress_bar_context_managers[0], nullcontext)
