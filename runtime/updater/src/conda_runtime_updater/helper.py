# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Invoke and validate the stamped runtime's version-one update helper."""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.exceptions import CondaError

if TYPE_CHECKING:
    from typing import Any

    from .metadata import RuntimeMetadata

ACTION_ENV = "CONDA_SHIP_INTERNAL_UPDATE"
CANDIDATE_ENV = "CONDA_SHIP_INTERNAL_UPDATE_CANDIDATE"
OFFLINE_ENV = "CONDA_SHIP_INTERNAL_UPDATE_OFFLINE"
PREFIX_ENV = "CONDA_SHIP_PREFIX"


def invoke_helper(
    runtime: RuntimeMetadata,
    action: str,
    *,
    candidate: str | None = None,
) -> dict[str, Any]:
    """Invoke one version-one action on the stamped outer executable."""

    env = os.environ.copy()
    env[PREFIX_ENV] = str(runtime.prefix)
    env[ACTION_ENV] = f"v1/{action}"
    env.pop(CANDIDATE_ENV, None)
    env.pop(OFFLINE_ENV, None)
    if candidate is not None:
        env[CANDIDATE_ENV] = candidate
    if context.offline:
        env[OFFLINE_ENV] = "1"

    try:
        result = subprocess.run(
            [runtime.executable],
            capture_output=True,
            check=False,
            encoding="utf-8",
            env=env,
            timeout=600,
        )
    except subprocess.TimeoutExpired as error:
        raise CondaError(
            f"Standalone conda executable {action} timed out after 600 seconds."
        ) from error
    except OSError as error:
        raise CondaError(
            f"Could not start the standalone conda executable for {action}: {error}"
        ) from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown helper error"
        raise CondaError(f"Standalone conda executable {action} failed: {detail}")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise CondaError(f"Standalone conda executable {action} returned invalid JSON.") from error
    if not isinstance(response, dict):
        raise CondaError(f"Standalone conda executable {action} returned invalid data.")
    return response


def validate_check(
    response: dict[str, Any],
    runtime: RuntimeMetadata,
) -> dict[str, Any]:
    """Validate the check fields used by the coordinator."""

    if not isinstance(response.get("available"), bool):
        raise CondaError("Standalone conda executable check omitted update availability.")
    if response.get("ownership") != runtime.ownership:
        raise CondaError("Standalone conda executable ownership changed during the update check.")
    if not response["available"]:
        return response

    version = response.get("version")
    digest = response.get("sha256")
    build_number = response.get("build_number")
    instruction = response.get("instruction")
    if not isinstance(version, str) or not version:
        raise CondaError("Standalone conda executable check omitted the candidate version.")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise CondaError("Standalone conda executable check returned an invalid SHA-256 digest.")
    if not isinstance(build_number, int) or isinstance(build_number, bool) or build_number < 0:
        raise CondaError("Standalone conda executable check returned an invalid build number.")
    if instruction is not None and (not isinstance(instruction, str) or not instruction.strip()):
        raise CondaError("Standalone conda executable check returned an invalid instruction.")
    return response
