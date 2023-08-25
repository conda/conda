# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.common.compat import on_win


def test_exports():
    import conda.exports

    assert conda.exports.PaddingError


def test_conda_subprocess():
    import os
    from subprocess import PIPE, Popen

    import conda

    try:
        p = Popen(
            ["echo", '"%s"' % conda.__version__],
            env=os.environ,
            stdout=PIPE,
            stderr=PIPE,
            shell=on_win,
        )
    except TypeError:
        for k, v in os.environ.items():
            if type(k) != str or type(v) != str:
                print(f"{k} ({type(k)}): {v} ({type(v)})")
        raise
    stdout, stderr = p.communicate()
    rc = p.returncode
    if rc != 0:
        raise CalledProcessError(rc, command, f"stdout: {stdout}\nstderr: {stderr}")
