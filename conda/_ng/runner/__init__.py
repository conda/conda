# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Runner façade: typed create/install requests and pluggable backends."""

from .classic_runner import ClassicCondaRunner, default_classic_runner
from .invocation import (
    CommandLiteral,
    InstallLikeInvocation,
    invocation_from_install_like,
)
from .protocol import PackageEnvironmentRunner
from .rattler_runner import RattlerRunner, default_rattler_runner
from .requests import build_create_request, build_install_request
from .shared_cli import (
    SHARED_CLI_CLASSIC,
    SHARED_CLI_RATTLER,
    dispatch_install_like,
    shared_cli_create_supported,
    shared_cli_engine,
    shared_cli_install_supported,
)
from .types import (
    AwaitingConfirmation,
    CreateRequest,
    InstallRequest,
    ProgressCallback,
    ProgressEvent,
    SolutionPlanReady,
    SolveFinished,
    SolveStarted,
    TransactionFinished,
    TransactionStarted,
    merge_specs_for_solve,
)

__all__ = [
    "AwaitingConfirmation",
    "ClassicCondaRunner",
    "CommandLiteral",
    "CreateRequest",
    "InstallLikeInvocation",
    "InstallRequest",
    "PackageEnvironmentRunner",
    "ProgressCallback",
    "ProgressEvent",
    "RattlerRunner",
    "SHARED_CLI_CLASSIC",
    "SHARED_CLI_RATTLER",
    "SolutionPlanReady",
    "SolveFinished",
    "SolveStarted",
    "TransactionFinished",
    "TransactionStarted",
    "build_create_request",
    "build_install_request",
    "default_classic_runner",
    "default_rattler_runner",
    "dispatch_install_like",
    "invocation_from_install_like",
    "merge_specs_for_solve",
    "shared_cli_create_supported",
    "shared_cli_engine",
    "shared_cli_install_supported",
]
