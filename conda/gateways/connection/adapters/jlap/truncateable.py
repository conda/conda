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
from typing import Tuple

DIGEST_SIZE = 32
MAX_LINEID_BYTES = 64


def hfunc(data: str, key: bytes):
    # blake2b(digest_size=32).hexdigest() is the maximum blake2b key length
    print(data, key.hex())
    return blake2b(data.encode("utf-8"), key=key, digest_size=DIGEST_SIZE)


def bhfunc(data: bytes, key: bytes):
    return blake2b(data, key=key, digest_size=DIGEST_SIZE)


def testlines():
    lines = "\n".join(str(x) for x in range(10))

    print(lines.splitlines())

    splits = lines.splitlines()

    iv = "0" * DIGEST_SIZE * 2

    lines = [iv] + splits

    def line_numbers(lines):
        """
        Generate hashed line numbers as a summary of all previous lines.
        """
        key = None
        for line in lines:
            if not key:
                key = bytes.fromhex(line)
                print(key.hex())
                continue
            key = hfunc(line, key).digest()
            yield (key, line)

    l0 = list(line_numbers(lines))

    print()
    print("\n".join(lines))

    while len(l0):
        print()
        f1 = [l0[0][0].hex()] + [l[1] for l in l0[1:]]
        print("\n".join(f1))
        print(l0[-1][0].hex())
        print()

        l1 = list(line_numbers(f1))

        l0 = l1


class JlapReader:
    def __init__(self, fp: RawIOBase):
        self.fp = fp
        self.lineid = bytes.fromhex(fp.readline().rstrip(b"\n").decode("utf-8"))
        assert len(self.lineid) <= MAX_LINEID_BYTES

    def read(self) -> Tuple[dict, bytes]:
        """
        Read one json line from file. Yield (line id, obj)
        """
        line = self.fp.readline()
        if not line.endswith(b"\n"):  # last line
            lineid_hex = self.lineid.hex()
            assert lineid_hex == line.decode("utf-8"), (
                "summary hash mismatch",
                lineid_hex,
                line,
            )
            return
        # without newline
        self.lineid = bhfunc(line[:-1], self.lineid).digest()
        return (json.loads(line), self.lineid)

    def readobjs(self):
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
    print(reader.lineid.hex())
    for line, hash in reader.readobjs():
        print(line, hash.hex())
    print(reader.lineid.hex())


if __name__ == "__main__":
    testlines()
    test()
