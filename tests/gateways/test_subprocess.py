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

    mock_stdout.write.assert_has_calls([
        call('1\n'),
        call(''),
        call('end\n'),
        call(''),
    ])

    mock_stderr.write.assert_has_calls([
        call('2\n'),
        call(''),
    ])

    assert resp.stdout == '1\nend\n'
    assert resp.stderr == "2\n"
    assert resp.rc == 0
