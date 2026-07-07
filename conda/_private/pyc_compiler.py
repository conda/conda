# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Compile explicit py/pyc path pairs for install transactions.

This script is executed by the target environment's Python, which may not have
conda installed. Keep it stdlib-only and do not import from conda.
"""

import errno
import json  # noqa: TID251 - the target Python may not be able to import conda
import os
import py_compile
import sys
import traceback


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        pairs = json.load(fh)

    for py_full_path, pyc_full_path in pairs:
        try:
            pyc_dir = os.path.dirname(pyc_full_path)
            if pyc_dir and not os.path.isdir(pyc_dir):
                try:
                    os.makedirs(pyc_dir)
                except OSError as exc:
                    if exc.errno != errno.EEXIST:
                        raise
            py_compile.compile(py_full_path, cfile=pyc_full_path, doraise=True)
        except Exception:
            traceback.print_exc()

    return 0


if __name__ == "__main__":
    sys.exit(main())
