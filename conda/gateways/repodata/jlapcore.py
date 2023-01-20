# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Small jlap reader.
"""

from __future__ import annotations

import logging
from collections import UserList
from hashlib import blake2b
from pathlib import Path
from typing import Iterable, Iterator, MutableSequence

log = logging.getLogger(__name__)


DIGEST_SIZE = 32  # 160 bits a minimum 'for security' length?
DEFAULT_IV = b"\0" * DIGEST_SIZE


def keyed_hash(data: bytes, key: bytes):
    """
    Keyed hash.
    """
    return blake2b(data, key=key, digest_size=DIGEST_SIZE)


def line_and_pos(lines: Iterable[bytes], pos=0) -> Iterator[tuple[int, bytes]]:
    """
    lines: iterator over input split by '\n', with '\n' removed.
    pos: initial position
    """
    for line in lines:
        yield pos, line
        pos += len(line) + 1


def jlap_buffer(
    lines: Iterable[bytes], iv: bytes, pos=0, verify=True
) -> MutableSequence[tuple[int, str, str]]:
    """
    :param lines: iterator over input split by b'\n', with b'\n' removed
    :param pos: initial position
    :param iv: initialization vector (first line of .jlap stream, hex decoded). Ignored if pos==0.
    :param verify: assert last line equals computed checksum of previous line.
        Useful for writing new .jlap files if False.

    :raises ValueError: if trailing and computed checksums do not match

    :return: list of (offset, line, checksum)
    """
    # save initial iv in case there were no new lines
    buffer: list[tuple[int, str, str]] = [(-1, iv.hex(), iv.hex())]
    initial_pos = pos

    for pos, line in line_and_pos(lines, pos=pos):
        if pos == 0:
            iv = bytes.fromhex(line.decode("utf-8"))
            buffer = [(0, iv.hex(), iv.hex())]
        else:
            iv = keyed_hash(line, iv).digest()
            buffer.append((pos, line.decode("utf-8"), iv.hex()))

    log.info("%d bytes read", pos - initial_pos)  # maybe + length of last line

    if verify:
        if buffer[-1][1] != buffer[-2][-1]:
            raise ValueError("checksum mismatch")
        else:
            log.info("Checksum OK")

    return buffer


def jlap_buffer_add(buffer: MutableSequence[tuple[int, str, str]], line: str):
    """
    Add line to buffer, following checksum rules.

    Buffer must not be empty.

    (Remember to pop trailing checksum and possibly trailing metadata line, if
    appending to a complete jlap file)

    Less efficient than creating a new buffer from many lines and our last iv,
    and extending.

    :return: buffer
    """
    if "\n" in line:
        raise ValueError("\\n not allowed in line")
    pos, last_line, iv = buffer[-1]
    # include last line's utf-8 encoded length, plus 1 in pos?
    pos += len(last_line.encode("utf-8")) + 1
    buffer.extend(jlap_buffer((line.encode("utf-8"),), bytes.fromhex(iv), pos, verify=False)[1:])
    return buffer


def jlap_buffer_terminate(buffer: MutableSequence[tuple[int, str, str]]):
    """
    Add trailing checksum to buffer.

    :return: buffer
    """
    pos, _, iv = buffer[-1]
    buffer = jlap_buffer_add(buffer, iv)
    return buffer


def jlap_buffer_write(buffer: MutableSequence[tuple[int, str, str]], path: Path | str):
    """
    Write buffer from jlap_buffer() to path.
    """
    with Path(path).open("w", encoding="utf-8", newline="\n") as p:
        return p.write("\n".join(b[1] for b in buffer))


def jlap_buffer_read(path: Path | str, verify=True):
    # in binary mode, line separatore is hardcoded as \n
    with Path(path).open("rb") as p:
        return jlap_buffer((line.rstrip(b"\n") for line in p), b"", verify=verify)


class JLAP(UserList):
    @classmethod
    def from_lines(cls, lines: Iterable[bytes], iv: bytes, pos=0, verify=True):
        return cls(jlap_buffer(lines, iv, pos=pos, verify=verify))

    @classmethod
    def from_path(cls, path: Path | str, verify=True):
        return cls(jlap_buffer_read(path, verify=verify))

    def add(self, line: str):
        jlap_buffer_add(self, line)
        return self

    def terminate(self):
        jlap_buffer_terminate(self)
        return self

    def write(self, path: Path):
        return jlap_buffer_write(self, path)
