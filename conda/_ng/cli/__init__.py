# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
conda._ng.cli — next-generation CLI layer (scaffolding).

This sub-package mirrors the structure of ``conda.cli`` and will
progressively absorb re-implemented commands.  For now every command
dispatches back to the classic implementation so that the routing
infrastructure can be exercised without any functional regression.
"""
