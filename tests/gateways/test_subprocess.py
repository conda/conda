# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import signal
import threading
import time
from textwrap import dedent

from pytest import CaptureFixture

from conda.gateways.subprocess import subprocess_call

_SIGNAL_READY_ENV = "CONDA_TEST_SIGNAL_READY_FILE"

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

    ready_file = os.environ.get("CONDA_TEST_SIGNAL_READY_FILE")
    if ready_file:
        with open(ready_file, "w") as handle:
            handle.write("ready")

    sys.stdout.write(f'child_ready:{os.getpid()}\\n')
    sys.stdout.flush()

    for _ in range(50):
        time.sleep(0.1)
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

    ready_file = os.environ.get("CONDA_TEST_SIGNAL_READY_FILE")
    if ready_file:
        with open(ready_file, "w") as handle:
            handle.write("ready")

    sys.stdout.write(f'child_ready:{os.getpid()}\\n')
    sys.stdout.flush()

    time.sleep(5)
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


def test_subprocess_call_forwards_interrupt_signals(tmp_path):
    """Test that interrupt signals are forwarded to subprocess groups."""
    from conda.common.compat import on_win

    script = _SIGNAL_HANDLER_SCRIPT_WINDOWS if on_win else _SIGNAL_HANDLER_SCRIPT_UNIX
    ready_file = tmp_path / "ready"
    env = os.environ.copy()
    env[_SIGNAL_READY_ENV] = str(ready_file)
    signal_to_send = signal.SIGBREAK if on_win else signal.SIGTERM

    result: dict = {"response": None, "exception": None, "signal_error": None}

    def raise_signal(signum):
        if on_win:
            if hasattr(signal, "raise_signal"):
                signal.raise_signal(signum)
            else:
                os.kill(os.getpid(), signum)
        else:
            os.kill(os.getpid(), signum)

    def send_signal():
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if ready_file.exists():
                try:
                    raise_signal(signal_to_send)
                except Exception as e:
                    result["signal_error"] = e
                return
            time.sleep(0.05)
        result["signal_error"] = RuntimeError("subprocess did not signal readiness")

    signal_thread = threading.Thread(target=send_signal)
    signal_thread.start()

    try:
        result["response"] = subprocess_call(
            ["python", "-c", script],
            env=env,
            capture_output=True,
            raise_on_error=False,
        )
    except Exception as e:
        result["exception"] = e
    finally:
        signal_thread.join(timeout=5)

    assert result["exception"] is None
    assert result["signal_error"] is None
    assert not signal_thread.is_alive()
    assert result["response"] is not None
    assert "child_ready:" in result["response"].stdout
    assert "child_received:" in result["response"].stdout
