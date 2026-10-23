# Writing files

`conda.gateways.disk.write` provides byte-oriented file reads and writes for conda
and downstream callers. Callers handle serialization, text encoding, and deciding
whether an edit needs to be written. For `.condarc` files, use
{ref}`ConfigurationFile <deep_dive_config_management>` instead.

## API

| API | Behavior |
| --- | --- |
| `read_file_snapshot(path) -> FileSnapshot` | Read bytes and capture the target's identity and metadata. |
| `write_file(path, data: bytes, *, expected: FileSnapshot \| None = None, allow_in_place: bool = False) -> FileSnapshot` | Write bytes and return the committed snapshot. |
| `FileSnapshot.data` | File contents as `bytes`, or `None` when the file does not exist. |

Snapshots are immutable. Use snapshots returned by these functions. Their
metadata and construction details are private. Their representation omits file
contents.

To write a complete file:

```python
from pathlib import Path

from conda.gateways.disk.write import write_file

path = Path("settings.json")
snapshot = write_file(path, b'{"enabled": true}\n')
```

`write_file()` publishes a write even when the bytes are unchanged. It does not
perform the caller's no-op detection.

## Read, modify, write

Pass the snapshot used to prepare an edit as `expected`:

```python
import json
from pathlib import Path

from conda.gateways.disk.write import read_file_snapshot, write_file

path = Path("settings.json")
snapshot = read_file_snapshot(path)
settings = (
    json.loads(snapshot.data.decode("utf-8")) if snapshot.data is not None else {}
)
settings["enabled"] = True
data = (json.dumps(settings) + "\n").encode("utf-8")
snapshot = write_file(path, data, expected=snapshot)
```

The returned snapshot can be passed as `expected` for the next edit. It describes
the file this call committed, without adopting a competing writer's later change.

`FileChangedError` reports a changed target, contents, identity, or metadata.
Replacing a file with identical bytes can therefore cause a conflict. Read again
and reapply the intended edit before retrying. Omitting `expected` starts tracking
the destination when `write_file()` begins. Checks during the write still apply,
but changes since an earlier caller read cannot be detected without its snapshot.

## Replacement and recovery

By default, writes use a staging file beside the destination and publish it with
`os.replace()`. Symlinks are followed to their resolved target. Replacement
changes the target's inode, so other hard links continue to refer to the old file.

On POSIX, `allow_in_place=True` permits overwriting an existing writable file when
directory permissions prevent staging a replacement. This fallback is
non-atomic. It attempts to restore the original bytes after a caught write error,
but cannot recover from process termination or a system crash. In-place writes
also affect other hard links to the file. `ConfigurationFile` enables this
fallback to support writable configuration files in read-only directories.

Filesystem and locking failures raise `OSError`, including:

- `FileChangedError` when a conflict is detected.
- `FileRestoreError` when both the in-place write and restoration fail. The file
  may contain partial data. Its `write_error` and `restore_error` attributes retain
  the original exceptions.
- `conda.exceptions.LockError` when a required lock cannot be acquired or released.

## Metadata, locking, and durability

Replacement preserves existing ownership, permissions, and supported extended
metadata. On macOS, this includes ACLs. On Windows, the original owner, group,
DACL, and integrity label are applied and verified before writing data. Resource
attributes, central access policy, and EFS protection are also checked. Failure
to preserve required protection aborts the write. The writer does not request
elevated privileges or copy audit ACEs. New files use the directory's normal
protection and process defaults.

Cooperating writers are serialized within a process and across processes. The
persistent `<target>.lock` file beside the resolved target must not be removed
while writers may exist. The index-cache `no_lock` setting does not disable these
locks.

Use trusted directories. Source and staging checks are separate from replacement,
so writers that ignore these locks can still race with an operation. The API does
not provide race-free protection against arbitrary writers or hostile directory
changes.

Written file data is flushed with `fsync()`. The parent directory is not synced,
so successful completion does not guarantee that a replacement survives a system
crash.
