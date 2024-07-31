# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pytest import CaptureFixture

from conda.gateways.subprocess import subprocess_call


def test_subprocess_call_without_capture_output(capfd: CaptureFixture):
    resp = subprocess_call(
        (
            'python -c "'
            "import sys, time; "
            "sys.stdout.write('1\\n'); "
            "sys.stderr.write('2\\n'); "
            "time.sleep(.3); "
            "sys.stdout.write('end\\n')"
            '"'
        ),
        capture_output=False,
    )

    stdout, stderr = capfd.readouterr()
    assert stdout.replace("\r\n", "\n") == "1\nend\n"
    assert stderr.replace("\r\n", "\n") == "2\n"
    assert resp.rc == 0


def test_subprocess_call_with_capture_output():
    resp = subprocess_call(
        (
            'python -c "'
            "import sys, time; "
            "sys.stdout.write('1\\n'); "
            "sys.stderr.write('2\\n'); "
            "time.sleep(.3); "
            "number = int(input('number=')); "
            "sys.stdout.write(f'{number * 2}\\n'); "
            "sys.stdout.write('end\\n')"
            '"'
        ),
        stdin="4",
        capture_output=True,
    )

    assert resp.stdout.replace("\r\n", "\n") == "1\nnumber=8\nend\n"
    assert resp.stderr.replace("\r\n", "\n") == "2\n"
    assert resp.rc == 0
