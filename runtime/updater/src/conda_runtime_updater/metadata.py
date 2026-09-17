# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Discover and validate stamped runtime metadata."""

from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from conda.exceptions import CondaError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any


@dataclass(frozen=True)
class RuntimeMetadata:
    prefix: Path
    path: Path
    version: str
    executable: Path
    lock_path: Path
    ownership: str
    instruction: str | None


def discover_runtime(prefix: Path) -> RuntimeMetadata | None:
    """Find one update-enabled conda runtime record in a root prefix."""

    matches = []
    for metadata_path in sorted(prefix.glob(".*.json")):
        candidate = read_runtime_metadata(prefix, metadata_path)
        if candidate is not None:
            matches.append(candidate)

    if len(matches) > 1:
        paths = ", ".join(str(runtime.path) for runtime in matches)
        raise CondaError(f"Multiple standalone conda runtime records were found: {paths}")
    return matches[0] if matches else None


def read_runtime_metadata(prefix: Path, metadata_path: Path) -> RuntimeMetadata | None:
    """Read one recognized runtime record and reject an invalid update identity."""

    try:
        metadata = metadata_path.lstat()
    except FileNotFoundError:
        return None
    if metadata_path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise CondaError(f"Runtime metadata is not a regular file: {metadata_path}")

    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CondaError(f"Could not read runtime metadata at {metadata_path}: {error}") from error
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != 1 or data.get("metadata_file") != metadata_path.name:
        return None
    if data.get("delegate_executable") != "conda":
        return None

    update = data.get("update")
    if update is None:
        return None
    if not isinstance(update, dict):
        raise CondaError(f"Runtime update metadata is invalid: {metadata_path}")

    version = require_string(data, "version", metadata_path)
    conda_version_from_runtime(version)

    ownership = require_string(update, "ownership", metadata_path)
    if ownership not in {"direct", "external"}:
        raise CondaError(f"Runtime update ownership is invalid: {metadata_path}")
    for key in ("artifact_name", "channel", "package", "sha256"):
        require_string(update, key, metadata_path)
    build_number = update.get("build-number")
    if not isinstance(build_number, int) or isinstance(build_number, bool) or build_number < 0:
        raise CondaError(f"Runtime update build number is invalid: {metadata_path}")

    instruction = update.get("instruction")
    if instruction is not None and (not isinstance(instruction, str) or not instruction.strip()):
        raise CondaError(f"Runtime update instruction is invalid: {metadata_path}")
    if ownership == "direct" and instruction is not None:
        raise CondaError(
            f"A directly managed runtime cannot have an external instruction: {metadata_path}"
        )

    executable = Path(require_string(update, "executable", metadata_path))
    if not executable.is_absolute() or not executable.is_file():
        raise CondaError(
            f"Runtime executable is missing or is not an absolute file path: {executable}"
        )

    stem = metadata_path.name.removesuffix(".json")
    lock_path = prefix / f"{stem}.update.lock"
    try:
        lock_metadata = lock_path.lstat()
    except FileNotFoundError as error:
        raise CondaError(f"Runtime update coordination lock is missing: {lock_path}") from error
    if lock_path.is_symlink() or not stat.S_ISREG(lock_metadata.st_mode):
        raise CondaError(f"Runtime update coordination lock is not a regular file: {lock_path}")
    if lock_metadata.st_size < 1:
        raise CondaError(f"Runtime update coordination lock is not initialized: {lock_path}")

    return RuntimeMetadata(
        prefix=prefix,
        path=metadata_path,
        version=version,
        executable=executable,
        lock_path=lock_path,
        ownership=ownership,
        instruction=instruction,
    )


def require_string(data: Mapping[str, Any], key: str, metadata_path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise CondaError(f"Runtime update field {key!r} is invalid: {metadata_path}")
    return value


def conda_version_from_runtime(version: str) -> str:
    """Return the bundled conda version from a runtime release version."""

    match = re.fullmatch(r"(?P<conda>[0-9]+\.[0-9]+\.[0-9]+)(?:\.post[0-9]+)?", version)
    if match is None:
        raise CondaError(f"Standalone conda runtime version is invalid: {version!r}")
    return match["conda"]
