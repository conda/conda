# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.gateways.subprocess import subprocess_call

try:
    from unittest.mock import patch, call
except ImportError:
    from mock import patch, call


@patch("sys.stderr", spec=True)
@patch("sys.stdout", spec=True)
def test_subprocess_call_with_live_stream(mock_stdout, mock_stderr):
    resp = subprocess_call(
        ('python -c "import sys, time; sys.stdout.write(\'1\\n\'); '
         'sys.stderr.write(\'2\\n\'); time.sleep(.3); sys.stdout.write(\'end\\n\')"'),
        live_stream=True,
    )

    def get_write_calls(mock_stream):
        return [args[0].replace('\r\n', '\n') for args, kw in mock_stream.write.call_args_list]

    stdout_calls = get_write_calls(mock_stdout)
    stderr_calls = get_write_calls(mock_stderr)

    assert ['1\n', '', 'end\n', ''] == stdout_calls
    assert ['2\n', ''] == stderr_calls

    assert resp.stdout.replace('\r\n', '\n') == '1\nend\n'
    assert resp.stderr.replace('\r\n', '\n') == "2\n"
    assert resp.rc == 0
