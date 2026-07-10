# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Detect CUDA version."""

from __future__ import annotations

import functools
import multiprocessing
import platform
import warnings
from typing import TYPE_CHECKING

from conda._private.cuda import cuda_driver_version_detector_target

from ...auxlib import NULL
from .. import hookimpl
from ..types import CondaVirtualPackage

if TYPE_CHECKING:
    from collections.abc import Iterable


def cuda_version():
    """
    Attempt to detect the version of CUDA present in the operating system.

    On Windows and Linux, the CUDA library is installed by the NVIDIA
    driver package, and is typically found in the standard library path,
    rather than with the CUDA SDK (which is optional for running CUDA apps).

    On macOS, the CUDA library is only installed with the CUDA SDK, and
    might not be in the library path.

    Returns: version string (e.g., '9.2') or None if CUDA is not found.
    """

    # Shortcut: CUDA is not available on macOS ARM64 (Apple Silicon)
    system = platform.system()
    machine = platform.machine()
    if system == "Darwin" and machine == "arm64":
        return NULL

    # Do not inherit file descriptors and handles from the parent process.
    # The `fork` start method should be considered unsafe as it can lead to
    # crashes of the subprocess. The `spawn` start method is preferred.
    try:
        context = multiprocessing.get_context("spawn")
        queue = context.SimpleQueue()
    except PermissionError as e:
        # If we can't create multiprocessing primitives (e.g., in a sandbox),
        # log a warning and skip CUDA detection
        warnings.warn(
            f"Unable to detect CUDA version due to permission error: {e}. "
            "Assuming CUDA is not available.",
            stacklevel=2,
        )
        return NULL

    # Spawn a subprocess to detect the CUDA version
    detector = context.Process(
        target=cuda_driver_version_detector_target,
        args=(queue,),
        name="CUDA driver version detector",
        daemon=True,
    )
    try:
        detector.start()
        detector.join(timeout=60.0)
    finally:
        # Always cleanup the subprocess
        detector.kill()  # requires Python 3.7+

    if queue.empty():
        return NULL

    result = queue.get()
    return result if result is not None else NULL


@functools.cache
def cached_cuda_version():
    """A cached version of the cuda detection system."""
    return cuda_version()


@hookimpl
def conda_virtual_packages() -> Iterable[CondaVirtualPackage]:
    # 1: __cuda==VERSION=0
    yield CondaVirtualPackage(
        name="cuda",
        version=cached_cuda_version,
        build=None,
        override_entity="version",
        # empty_override=NULL,  # falsy override → skip __cuda
    )
