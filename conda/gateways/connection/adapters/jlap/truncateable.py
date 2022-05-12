# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""
Truncatable log format. Save summary hash of any number of earlier lines then
append new data.

<initial> line line line <summary hash>

The hash of each line is hash(line, key=hash(line-1)) The hash of line 1 is
hash(line, key=line0.decode('hex'))

The newline character is not included in the hash.

The last line is hash(line -1).hexdigest().

The last line does not end with a line separator, so there is no blank line at
the end of the file.
"""

from hashlib import blake2b
from io import RawIOBase, BytesIO
import json
from typing import Tuple, BinaryIO, Optional, Iterator

DIGEST_SIZE = 32
MAX_LINEID_BYTES = 64


def hfunc(data: str, key: bytes):
    # blake2b(digest_size=32).hexdigest() is the maximum blake2b key length
    return blake2b(data.encode("utf-8"), key=key, digest_size=DIGEST_SIZE)


def bhfunc(data: bytes, key: bytes):
    return blake2b(data, key=key, digest_size=DIGEST_SIZE)


JlapReaderLine = Tuple[dict, bytes]


class JlapReader:
    def __init__(self, fp: BinaryIO):
        self.fp = fp
        self.line_id = bytes.fromhex(fp.readline().rstrip(b"\n").decode("utf-8"))
        assert len(self.line_id) <= MAX_LINEID_BYTES

    def read(self) -> Optional[JlapReaderLine]:
        """
        Read one json line from file reading from the currently open `fp` attribute.
        """
        line = self.fp.readline()
        if not line.endswith(b"\n"):  # last line
            line_id_hex = self.line_id.hex()
            assert line_id_hex == line.decode("utf-8"), (
                "summary hash mismatch",
                line_id_hex,
                line,
            )
            return

        # without newline
        self.line_id = bhfunc(line[:-1], self.line_id).digest()
        return json.loads(line), self.line_id

    def read_objs(self) -> Iterator[JlapReaderLine]:
        obj = True
        while obj:
            obj = self.read()
            if obj:
                yield obj


class JlapWriter:
    def __init__(self, fp: RawIOBase, lineid: bytes = ("0" * DIGEST_SIZE * 2)):
        lineid = bytes.fromhex(lineid)
        self.fp = fp
        self.fp.write(lineid.hex().encode("utf-8") + b"\n")
        self.lineid = lineid

    def write(self, obj):
        """
        Write one json line to file.
        """
        line = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.lineid = bhfunc(line, self.lineid).digest()
        self.fp.write(line)
        self.fp.write(b"\n")

    def finish(self):
        self.fp.write(self.lineid.hex().encode("utf-8"))


def test():
    """
    TODO: Move this actual tests
    """
    bio = BytesIO()
    writer = JlapWriter(bio, ("0" * DIGEST_SIZE * 2))
    for i in range(10):
        writer.write(i)
    writer.finish()

    print()

    print(bio.getvalue().decode("utf-8"))

    bio.seek(0)

    print("\nreading")

    reader = JlapReader(bio)
    print(reader.line_id.hex())
    for line, hash in reader.read_objs():
        print(line, hash.hex())
    print(reader.line_id.hex())


def testlines():
    """
    TODO: Move this actual tests
    """
    lines = "\n".join(str(x) for x in range(10))

    print(lines.splitlines())

    splits = lines.splitlines()

    iv = "0" * DIGEST_SIZE * 2

    lines = [iv] + splits

    def line_numbers(lines_):
        """
        Generate hashed line numbers as a summary of all previous lines.
        """
        key = None
        for line in lines_:
            if not key:
                key = bytes.fromhex(line)
                print(key.hex())
                continue
            key = hfunc(line, key).digest()
            yield key, line

    lines_0 = list(line_numbers(lines))

    print()
    print("\n".join(lines))

    while len(lines_0):
        print()
        f1 = [lines_0[0][0].hex()] + [line[1] for line in lines_0[1:]]
        print("\n".join(f1))
        print(lines_0[-1][0].hex())
        print()

        lines_1 = list(line_numbers(f1))

        lines_0 = lines_1
