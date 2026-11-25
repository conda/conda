# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Event types used to communicate with reporter backends.

Events are immutable data objects sent through
:meth:`conda.reporters.CondaReporter.send`, which hands each event to
:meth:`conda.plugins.types.ReporterRendererBase.handle`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    """
    Immutable base class for all reporter events.
    """
