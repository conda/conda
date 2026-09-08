# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Verify that importing conda.common.io does not eagerly load concurrency modules."""

from __future__ import annotations

import subprocess
import sys
import textwrap


def test_io_does_not_eagerly_import_concurrent_futures() -> None:
    """concurrent.futures should only load when executor classes are accessed."""
    snippet = textwrap.dedent("""\
        import sys
        import conda.common.io
        print("concurrent.futures" in sys.modules)
    """)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Probe failed: {result.stderr}"
    assert result.stdout.strip() == "False", (
        "concurrent.futures was loaded at import time; it should be deferred"
    )


def test_lazy_executor_classes_work() -> None:
    """DummyExecutor and ThreadLimitedThreadPoolExecutor should still work when accessed."""
    snippet = textwrap.dedent("""\
        import sys
        from conda.common.io import DummyExecutor, ThreadLimitedThreadPoolExecutor, as_completed
        assert "concurrent.futures" in sys.modules
        e = DummyExecutor()
        f = e.submit(lambda: 42)
        assert f.result() == 42
        e.shutdown()
        print("ok")
    """)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Probe failed: {result.stderr}"
    assert result.stdout.strip() == "ok"
