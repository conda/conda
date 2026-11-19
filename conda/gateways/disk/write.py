# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Publish complete files with metadata preservation and change detection."""

from __future__ import annotations

import os
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from shutil import copystat
from stat import S_IMODE
from threading import Lock
from typing import TYPE_CHECKING
from uuid import uuid4

from ...common.compat import on_mac, on_win

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import BinaryIO

__all__ = [
    "FileChangedError",
    "FileRestoreError",
    "FileSnapshot",
    "read_file_snapshot",
    "write_file",
]


class FileChangedError(OSError):
    """The file or its containing directory changed during an operation."""

    def __init__(self, path: Path, when: str) -> None:
        super().__init__(
            f"File at {path}: file changed {when}. Read the file again before retrying."
        )


class FileRestoreError(OSError):
    """An in-place write and the attempt to restore its original bytes failed."""

    def __init__(
        self, path: Path, write_error: OSError, restore_error: OSError
    ) -> None:
        self.write_error = write_error
        self.restore_error = restore_error
        super().__init__(
            f"Cannot write file at {path}: {write_error}. "
            f"Restoring the original contents also failed: {restore_error}"
        )


@dataclass(frozen=True)
class FileSnapshot:
    """An observed file version. Obtain one with :func:`read_file_snapshot`.

    ``data`` contains the file's bytes, or None if it does not exist.
    """

    data: bytes | None = field(repr=False)
    _path: Path = field(repr=False, compare=False)
    _target: Path = field(repr=False)
    _metadata: os.stat_result | None = field(repr=False, compare=False)
    _security: bytes | None = field(repr=False)
    _version: tuple[int, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_version", _file_version(self._metadata))

    @property
    def _state(self) -> tuple[Path, bytes | None, tuple[int, ...], bytes | None]:
        return self._target, self.data, self._version, self._security


_write_lock = Lock()


def _reset_write_lock() -> None:
    global _write_lock
    _write_lock = Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_write_lock)


@contextmanager
def _lock_source(source: BinaryIO) -> Iterator[None]:
    """Keep a POSIX file locked when other descriptors are opened and closed."""
    import fcntl
    from time import sleep

    from ...exceptions import LockError
    from .lock import LOCK_ATTEMPTS, LOCK_SLEEP

    for attempt in range(LOCK_ATTEMPTS):
        try:
            fcntl.flock(source, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if attempt == LOCK_ATTEMPTS - 1:
                raise LockError("Failed to acquire file lock.")
            sleep(LOCK_SLEEP)
    try:
        yield
    finally:
        fcntl.flock(source, fcntl.LOCK_UN)


def _file_version(metadata: os.stat_result | None) -> tuple[int, ...]:
    if metadata is None:
        return ()
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        getattr(metadata, "st_flags", 0),
        getattr(metadata, "st_file_attributes", 0),
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _read_file(
    path: Path,
) -> tuple[Path, bytes | None, os.stat_result | None, bytes | None]:
    """Read one file version, checking its descriptor and resolved path."""
    from ...common._os.windows import get_file_security

    target = path.resolve()
    try:
        source = target.open("rb")
    except FileNotFoundError:
        if path.resolve() == target and not target.exists():
            return target, None, None, None
    else:
        with source:
            before = os.fstat(source.fileno())
            security = None
            if on_win:
                security = get_file_security(source.fileno())
            data = source.read()
            if on_win and get_file_security(source.fileno()) != security:
                raise FileChangedError(path, "while reading security")
            try:
                current = target.stat()
            except FileNotFoundError:
                current = None
            resolved = path.resolve()
            after = os.fstat(source.fileno())
            # Windows stat and fstat can report different meanings of ctime.
            # Compare versions through descriptors and paths by identity only.
            if (
                resolved == target
                and current is not None
                and os.path.samestat(after, current)
                and _file_version(before) == _file_version(after)
            ):
                return target, data, after, security

    raise FileChangedError(path, "while reading")


def read_file_snapshot(path: str | os.PathLike[str]) -> FileSnapshot:
    """Read bytes and remember the resolved file's identity and security metadata.

    Args:
        path: File to read. Symlinks are followed.

    Returns:
        A snapshot with data=None for a missing file.

    Raises:
        FileChangedError: The file changed while it was being read.
        OSError: The file could not be read.
    """
    path = Path(path)
    target, data, metadata, security = _read_file(path)
    return FileSnapshot(data, path.absolute(), target, metadata, security)


def write_file(
    path: str | os.PathLike[str],
    data: bytes,
    *,
    expected: FileSnapshot | None = None,
    allow_in_place: bool = False,
) -> FileSnapshot:
    """Stage complete bytes beside a file, then replace its resolved target.

    Participating writers use a persistent sibling ``<name>.lock`` file.
    Do not remove that file while other writers may use it. Existing file
    permissions and supported security metadata are preserved. Even identical
    bytes are published again and refresh the file's modification time.

    Args:
        path: Destination file. Its parent directory must exist.
        data: Complete contents, already encoded as bytes.
        expected: Reject changes since this snapshot, including file creation
            or deletion. With None, only check changes during this operation.
        allow_in_place: On POSIX, allow writing an existing writable file in
            place when permissions prevent creating a sibling temporary file.
            This attempts restoration on write errors but is not atomic.

    Returns:
        The committed file snapshot, usable as expected for another write.

    Raises:
        TypeError: data is not bytes.
        FileChangedError: A change was detected before publication.
        FileRestoreError: An in-place write and restoration both failed.
        OSError: Reading, locking, preserving metadata or writing failed.

    The staged file is synced before replacement. Its containing directory is
    not synced. Locks are advisory and cannot exclude uncooperative writers.
    """
    from ...common._os.windows import get_file_security
    from .lock import lock

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")

    path = Path(path)
    source_fd = None
    temporary = None
    temporary_metadata = None

    def conflict(when: str) -> FileChangedError:
        return FileChangedError(path, when)

    try:
        target, previous_data, metadata, security = _read_file(path)
        state = (target, previous_data, _file_version(metadata), security)
        if expected is not None and state != expected._state:
            raise conflict("after reading")

        def source_changed() -> bool:
            current_target, current_data, current_metadata, current_security = (
                _read_file(path)
            )
            return state != (
                current_target,
                current_data,
                _file_version(current_metadata),
                current_security,
            )

        parent_metadata = target.parent.stat()
        lock_path = target.with_name(f"{target.name}.lock")
        with _write_lock, ExitStack() as stack:
            locked_source = None
            if metadata is not None and not on_win:
                locked_source = stack.enter_context(target.open("r+b", buffering=0))
                stack.enter_context(_lock_source(locked_source))
                if _file_version(os.fstat(locked_source.fileno())) != _file_version(
                    metadata
                ):
                    raise conflict("while waiting to write")
            try:
                lock_file = stack.enter_context(lock_path.open("a+"))
            except PermissionError:
                if locked_source is None:
                    raise
                lock_metadata = None
            else:
                stack.enter_context(lock(lock_file, required=True))
                lock_metadata = os.fstat(lock_file.fileno())

            def paths_changed() -> bool:
                try:
                    return not (
                        os.path.samestat(parent_metadata, target.parent.stat())
                        and (
                            lock_metadata is None
                            or os.path.samestat(lock_metadata, lock_path.lstat())
                        )
                    )
                except FileNotFoundError:
                    return True

            if paths_changed() or source_changed():
                raise conflict("while waiting to write")
            if metadata is not None:
                write_fd = os.open(target, os.O_WRONLY)
                os.close(write_fd)
                if on_mac or on_win:
                    source_fd = os.open(target, os.O_RDONLY)
                    if _file_version(os.fstat(source_fd)) != _file_version(metadata):
                        raise conflict("while writing")
                    if on_win:
                        if get_file_security(source_fd) != security:
                            raise conflict("while writing")

            candidate = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
            if metadata is None:
                mode = 0o666
            else:
                mode = 0 if on_mac else S_IMODE(metadata.st_mode)
            try:
                if on_win and security is not None and metadata is not None:
                    from stat import FILE_ATTRIBUTE_ENCRYPTED

                    from ...common._os.windows import create_file_with_security

                    fd = create_file_with_security(
                        candidate,
                        security,
                        encrypted_source=(
                            target
                            if metadata.st_file_attributes & FILE_ATTRIBUTE_ENCRYPTED
                            else None
                        ),
                    )
                else:
                    fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
            except PermissionError:
                if not allow_in_place or locked_source is None:
                    raise
                # A writable file can live in a directory that forbids replacement.
                # Preserve that behavior, with best-effort recovery on write errors.
                stream = locked_source
                if paths_changed() or source_changed():
                    raise conflict("while writing")
                original = stream.read()

                def overwrite(content: bytes) -> None:
                    stream.seek(0)
                    if os.write(stream.fileno(), content) != len(content):
                        raise OSError("Incomplete file write")
                    stream.truncate(len(content))
                    os.fsync(stream.fileno())

                try:
                    overwrite(data)
                except OSError as error:
                    try:
                        overwrite(original)
                    except OSError as restore_error:
                        raise FileRestoreError(path, error, restore_error) from error
                    raise
                return FileSnapshot(
                    data, path.absolute(), target, os.fstat(stream.fileno()), security
                )
            temporary = candidate
            temporary_metadata = os.fstat(fd)
            with os.fdopen(fd, "wb") as stream:
                if metadata is not None:
                    if on_mac:
                        from ...common._os.osx import copy_acl

                        copy_acl(source_fd, stream.fileno())
                    if hasattr(os, "chown"):
                        if (
                            temporary_metadata.st_uid,
                            temporary_metadata.st_gid,
                        ) != (metadata.st_uid, metadata.st_gid):
                            os.chown(temporary, metadata.st_uid, metadata.st_gid)
                    copystat(target, temporary)
                    if source_changed():
                        raise conflict("while writing")
                if stream.write(data) != len(data):
                    raise OSError("Incomplete file write")
                stream.flush()
                # Refresh timestamps even when publishing an empty file.
                os.utime(temporary, None)
                os.fsync(stream.fileno())
                staged_metadata = os.fstat(stream.fileno())
                staged_security = None
                if on_win:
                    staged_security = get_file_security(stream.fileno())
                    if security is not None and staged_security != security:
                        raise conflict("while writing")

            _, staged_data, closed_metadata, closed_security = _read_file(temporary)
            # Windows can finalize timestamps when the writing handle closes.
            # Contents, identity, and access metadata must still match.
            version_end = -2 if on_win else None
            if (
                staged_data != data
                or closed_metadata is None
                or closed_security != staged_security
                or _file_version(staged_metadata)[:version_end]
                != _file_version(closed_metadata)[:version_end]
            ):
                raise conflict("while writing")
            staged_metadata = closed_metadata
            with temporary.open("rb") as staged:
                if (
                    paths_changed()
                    or source_changed()
                    or not os.path.samestat(staged_metadata, temporary.lstat())
                    or (
                        on_win and get_file_security(staged.fileno()) != staged_security
                    )
                    or _file_version(os.fstat(staged.fileno()))
                    != _file_version(staged_metadata)
                ):
                    raise conflict("while writing")
            if source_fd is not None:
                os.close(source_fd)
                source_fd = None
            os.replace(temporary, target)
            temporary = None
            snapshot = FileSnapshot(
                data, path.absolute(), target, staged_metadata, staged_security
            )
            # Rename may change ctime. Only refresh it from our staged file,
            # never from a replacement or different contents written later.
            try:
                (
                    committed_target,
                    committed_data,
                    committed_metadata,
                    committed_security,
                ) = _read_file(path)
            except OSError:
                pass
            else:
                if (
                    committed_target == target
                    and committed_data == data
                    and committed_metadata is not None
                    and committed_security == staged_security
                    and _file_version(staged_metadata)[:-1]
                    == _file_version(committed_metadata)[:-1]
                ):
                    snapshot = FileSnapshot(
                        data,
                        path.absolute(),
                        target,
                        committed_metadata,
                        committed_security,
                    )
            return snapshot
    finally:
        if source_fd is not None:
            os.close(source_fd)
        if temporary is not None:
            try:
                if temporary_metadata is not None and os.path.samestat(
                    temporary_metadata, temporary.lstat()
                ):
                    temporary.unlink()
            except FileNotFoundError:
                pass
