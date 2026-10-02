# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Show advisory runtime updates using the stamped executable's cached catalog."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from time import time
from typing import TYPE_CHECKING

from conda.base.context import context
from platformdirs import user_cache_dir

from .helper import probe_runtime
from .metadata import discover_runtime

if TYPE_CHECKING:
    from typing import Any

    from .metadata import RuntimeMetadata

DAY = 86_400


def cache_path(runtime: RuntimeMetadata) -> Path:
    identity = json.dumps([str(runtime.executable), str(runtime.prefix), runtime.version])
    key = hashlib.sha256(identity.encode()).hexdigest()
    return Path(user_cache_dir("conda-runtime-updater")) / f"{key}.json"


def read_state(path: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def write_state(path: Path, state: dict[str, Any]) -> None:
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(state, stream, allow_nan=False)
        os.replace(temporary, path)
    except (OSError, ValueError):
        pass
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def within_day(timestamp: Any, now: float) -> bool:
    if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool):
        return False
    try:
        return 0 <= now - float(timestamp) < DAY
    except OverflowError:
        return False


def format_cache_age(seconds: int | None) -> str:
    if seconds is None:
        return "age unknown"
    for unit, length in (("day", DAY), ("hour", 3600), ("minute", 60), ("second", 1)):
        if seconds >= length or length == 1:
            count = seconds // length
            return f"{count} {unit}{'' if count == 1 else 's'} old"
    raise AssertionError("unreachable cache age")


def notification_text(runtime: RuntimeMetadata, response: dict[str, Any]) -> str:
    current = f"{response['current_version']} (build {response['current_build_number']})"
    candidate = f"{response['version']} (build {response['build_number']})"
    if response["source"] == "cache":
        age = format_cache_age(response["cache_age_seconds"])
        message = f"Cached channel metadata ({age}) lists a conda runtime update:"
    else:
        message = "A conda runtime update is available:"
    if runtime.ownership == "direct":
        instruction = "Run `conda self update` to update."
    else:
        instruction = (
            response.get("instruction")
            or runtime.instruction
            or "Update the conda executable with the package manager that installed it."
        )
    return f"{message}\n  {current} -> {candidate}\n{instruction}"


def notify(command: str) -> None:
    """Offer an update after an eligible core command returns successfully."""

    del command
    try:
        if (
            context.quiet
            or context.json
            or context.dry_run
            or not context.plugins.runtime_update_notifications
            or not all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr))
        ):
            return
        runtime = discover_runtime(Path(context.root_prefix))
        if runtime is None:
            return

        now = time()
        path = cache_path(runtime)
        state = read_state(path)
        offline = context.offline or within_day(state.get("checked_at"), now)
        if not offline:
            # Failed online attempts also wait until the next day. An offline
            # command leaves this timestamp alone so reconnecting can check.
            state["checked_at"] = now
            write_state(path, state)
        response = probe_runtime(runtime, offline=offline)
        if response is None or response.get("available") is not True:
            return

        candidate = [response["version"], response["build_number"], response["sha256"]]
        if state.get("candidate") == candidate and within_day(state.get("notified_at"), now):
            return
        state.update(candidate=candidate, notified_at=now)
        write_state(path, state)
        print(f"\n{notification_text(runtime, response)}\n", file=sys.stderr)
    except Exception:
        # Advisory failures must not change the successful command's result.
        return
