# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import signal
import sys
import threading
import time
from textwrap import dedent

from pytest import CaptureFixture

from conda.gateways.subprocess import subprocess_call

_SIGNAL_HANDLER_SCRIPT_WINDOWS = dedent("""
    import os
    import signal
    import sys
    import time

    def signal_handler(signum, frame):
        sys.stdout.write(f'child_received:{signum}\\n')
        sys.stdout.flush()
        sys.exit(0)

    signal.signal(signal.SIGBREAK, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    sys.stdout.write(f'child_ready:{os.getpid()}\\n')
    sys.stdout.flush()

    time.sleep(10)
""")

_SIGNAL_HANDLER_SCRIPT_UNIX = dedent("""
    import os
    import signal
    import sys
    import time

    def signal_handler(signum, frame):
        sys.stdout.write(f'child_received:{signum}\\n')
        sys.stdout.flush()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sys.stdout.write(f'child_ready:{os.getpid()}\\n')
    sys.stdout.flush()

    time.sleep(10)
""")


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


def test_subprocess_call_forwards_interrupt_signals():
    """Test that interrupt signals are forwarded to subprocess groups."""
    ON_WINDOWS = sys.platform == "win32"
    script = (
        _SIGNAL_HANDLER_SCRIPT_WINDOWS if ON_WINDOWS else _SIGNAL_HANDLER_SCRIPT_UNIX
    )

    def run_subprocess_and_signal():
        from subprocess import CalledProcessError

        try:
            resp = subprocess_call(
                ["python", "-c", script],
                capture_output=True,
                raise_on_error=False,
            )
            return resp
        except CalledProcessError as e:
            return e.output

    result: dict = {"response": None, "exception": None}

    def target():
        try:
            result["response"] = run_subprocess_and_signal()
        except Exception as e:
            result["exception"] = e

    thread = threading.Thread(target=target)
    thread.start()

    # Give the subprocess time to start and register signal handlers
    time.sleep(0.5)

    from conda import ACTIVE_SUBPROCESSES

    if ACTIVE_SUBPROCESSES:
        proc = list(ACTIVE_SUBPROCESSES)[0]
        if ON_WINDOWS:
            os.kill(proc.pid, signal.CTRL_BREAK_EVENT)  # type: ignore
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

    thread.join(timeout=5)

    assert result["response"] is not None
    assert "child_ready:" in result["response"].stdout
    assert "child_received:" in result["response"].stdout or result["response"].rc != 0
