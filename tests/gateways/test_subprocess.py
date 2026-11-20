# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import signal
import sys
import threading
import time

import pytest
from pytest import CaptureFixture

from conda import conda_signal_handler
from conda.common.compat import on_win
from conda.common.signals import signal_handler
from conda.exceptions import CondaSignalInterrupt
from conda.gateways.subprocess import subprocess_call, subprocess_call_with_clean_env


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


def test_subprocess_call_with_clean_env_deprecated():
    with pytest.deprecated_call():
        subprocess_call_with_clean_env('python -c "pass"')


@pytest.mark.skipif(on_win, reason="POSIX signal handling")
def test_subprocess_call_preserves_outer_signal_handler():
    def interrupt_parent():
        os.kill(os.getpid(), signal.SIGINT)

    timer = threading.Timer(0.5, interrupt_parent)
    timer.start()
    try:
        with pytest.raises(CondaSignalInterrupt):
            with signal_handler(conda_signal_handler):
                subprocess_call(
                    [sys.executable, "-c", "import time; time.sleep(30)"],
                    raise_on_error=False,
                )
    finally:
        timer.cancel()


@pytest.mark.skipif(on_win, reason="POSIX process groups")
def test_subprocess_call_forwards_signals_to_process_group(tmp_path):
    pid_path = tmp_path / "grandchild.pid"

    grandchild_code = (
        "import os, sys, time; "
        "open(sys.argv[1], 'w').write(str(os.getpid())); "
        "time.sleep(30)"
    )
    child_code = (
        "import subprocess, sys; "
        "process = subprocess.Popen([sys.executable, '-c', sys.argv[2], sys.argv[1]]); "
        "process.wait()"
    )

    def interrupt_parent():
        os.kill(os.getpid(), signal.SIGTERM)

    timer = threading.Timer(0.5, interrupt_parent)
    timer.start()
    try:
        response = subprocess_call(
            [sys.executable, "-c", child_code, str(pid_path), grandchild_code],
            raise_on_error=False,
            forward_signals=True,
        )
    finally:
        timer.cancel()

    assert response.rc == -signal.SIGTERM

    grandchild_pid = int(pid_path.read_text())
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(grandchild_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        pytest.fail(f"grandchild process {grandchild_pid} still running")
