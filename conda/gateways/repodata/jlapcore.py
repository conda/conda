# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Small jlap reader.
"""

from __future__ import annotations

import logging
from hashlib import blake2b
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)


DIGEST_SIZE = 32  # 160 bits a minimum 'for security' length?


def keyed_hash(data: bytes, key: bytes):
    """
    Keyed hash.
    """
    return blake2b(data, key=key, digest_size=DIGEST_SIZE)


def line_and_pos(lines: Iterator[bytes], pos=0) -> Iterator[tuple[int, bytes]]:
    """
    lines: iterator over input split by '\n', with '\n' removed.
    pos: initial position
    """
    for line in lines:
        yield pos, line
        pos += len(line) + 1


def jlap_buffer(
    lines: Iterator[bytes], iv: bytes, pos=0, verify=True
) -> list[tuple[int, str, str]]:
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


def write_jlap_buffer(path: Path, buffer: list[tuple[int, str, str]]):
    """
    Write buffer from jlap_buffer() to path.
    """
    path.write_text("\n".join(b[1] for b in buffer), encoding="utf-8", newline="\n")
