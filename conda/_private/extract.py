# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Lean package extraction helpers for subprocess workers."""

from __future__ import annotations

import os
import pickle

# This module is imported in each spawned extraction worker. Keep imports here
# limited to the standard library; importing conda runtime state defeats the
# process pool's startup benefit.


def _debug_archive(
    stage: str,
    path: str | os.PathLike,
    *,
    error: BaseException | None = None,
    **details: object,
) -> None:
    """Save temporary diagnostics for the channel-priority test archives."""
    output_dir = os.environ.get("CONDA_TEST_ARCHIVE_DEBUG")
    filename = os.path.basename(path)
    if not output_dir or not filename.startswith(
        ("dependent-", "dependency-", "versioned-")
    ):
        return

    import hashlib
    import time
    import traceback

    record: dict[str, object] = {
        "stage": stage,
        "file": filename,
        "test": os.environ.get("PYTEST_CURRENT_TEST"),
        "time_ns": time.time_ns(),
        **details,
    }
    try:
        with open(path, "rb") as archive:
            data = archive.read()
        record.update(
            size=len(data),
            header=data[:8].hex(),
            sha256=hashlib.sha256(data).hexdigest(),
        )
    except OSError as read_error:
        record["read_error"] = type(read_error).__name__
        record["errno"] = read_error.errno

    if error is not None:
        chain = []
        while error is not None:
            message = str(error).replace(os.fspath(path), filename)
            chain.append(
                {
                    "type": f"{type(error).__module__}.{type(error).__qualname__}",
                    "message": message
                    if "/" not in message and "\\" not in message
                    else None,
                    "frames": [
                        (os.path.basename(frame.filename), frame.lineno, frame.name)
                        for frame in traceback.extract_tb(error.__traceback__)
                    ],
                }
            )
            error = error.__cause__ or (
                None if error.__suppress_context__ else error.__context__
            )
        record["exceptions"] = chain

    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(
            os.path.join(output_dir, f"{os.getpid()}.log"), "a", encoding="utf-8"
        ) as diagnostics:
            diagnostics.write(f"{record!r}\n")
    except OSError:
        return


def extract_conda_package_archive(
    source_full_path: str | os.PathLike,
    destination_directory: str | os.PathLike,
    *,
    ensure_picklable_errors: bool = False,
) -> None:
    """Extract a conda package archive without importing conda runtime state.

    Args:
        source_full_path: Package archive to extract.
        destination_directory: Directory to extract into.
        ensure_picklable_errors: Replace exceptions that cannot survive a pickle
            round trip with a plain ``RuntimeError``.
    """
    import conda_package_handling.api

    _debug_archive("extract-before", source_full_path)
    try:
        conda_package_handling.api.extract(
            os.fspath(source_full_path),
            dest_dir=os.fspath(destination_directory),
        )
    except Exception as error:
        _debug_archive("extract-failed", source_full_path, error=error)
        if not ensure_picklable_errors:
            raise
        try:
            # Some exceptions can be serialized but not reconstructed.
            pickle.loads(pickle.dumps(error))
        except Exception:
            error_type = f"{type(error).__module__}.{type(error).__qualname__}"
            raise RuntimeError(f"{error_type}: {error}") from None
        raise
