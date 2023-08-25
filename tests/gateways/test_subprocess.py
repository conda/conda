# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.gateways.subprocess import subprocess_call


def test_subprocess_call_with_capture_output(capfd):
    resp = subprocess_call(
        (
            "python -c \"import sys, time; sys.stdout.write('1\\n'); "
            "sys.stderr.write('2\\n'); time.sleep(.3); sys.stdout.write('end\\n')\""
        ),
        capture_output=False,
    )

    captured = capfd.readouterr()
    assert captured.out.replace("\r\n", "\n") == "1\nend\n"
    assert captured.err.replace("\r\n", "\n") == "2\n"
    assert resp.rc == 0


def test_subprocess_call_without_capture_output():
    resp = subprocess_call(
        (
            "python -c \"import sys, time; sys.stdout.write('1\\n'); "
            "sys.stderr.write('2\\n'); time.sleep(.3); sys.stdout.write('end\\n')\""
        ),
        capture_output=True,
    )

    assert resp.stdout.replace("\r\n", "\n") == "1\nend\n"
    assert resp.stderr.replace("\r\n", "\n") == "2\n"
    assert resp.rc == 0
