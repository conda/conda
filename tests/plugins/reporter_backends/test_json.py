# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.common.serialize import json
from conda.plugins.reporter_backends.json import (
    JSONProgressBar,
    JSONReporterRenderer,
    JSONSpinner,
)


def test_json_handler():
    """
    Tests the JSONReporterHandler ReporterHandler class
    """
    test_data = {"one": "value_one", "two": "value_two", "three": "value_three"}
    test_envs = ["env_one", "env_two"]
    test_envs_dict = {"envs": test_envs}
    test_str = "a string value"
    json_handler_object = JSONReporterRenderer()

    assert json_handler_object.detail_view(test_data) == json.dumps(test_data)
    assert json_handler_object.envs_list(test_envs) == json.dumps({"envs": test_envs})
    assert json_handler_object.envs_list(test_envs_dict) == json.dumps(
        {"envs": test_envs}
    )
    assert json_handler_object.render(test_str) == json.dumps(test_str)


def test_json_progress_bar_enabled(mocker):
    """
    Test the case for when the progress bar is enabled
    """
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")

    progress_bar = JSONProgressBar("test", enabled=True)

    progress_bar.update_to(0.3)
    progress_bar.refresh()  # doesn't do anything; called for coverage
    progress_bar.close()

    assert mock_stdout.write.mock_calls == [
        mocker.call(
            '{"fetch":"test","finished":false,"maxval":1,"progress":0.300000}\n\x00'
        ),
        mocker.call('{"fetch":"test","finished":true,"maxval":1,"progress":1}\n\x00'),
    ]


def test_json_progress_bar_not_enabled(mocker):
    """
    Test the case for when the progress bar is not enabled
    """
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")

    progress_bar = JSONProgressBar("test", enabled=False)

    progress_bar.update_to(0.3)
    progress_bar.refresh()  # doesn't do anything; called for coverage
    progress_bar.close()

    assert mock_stdout.write.mock_calls == []


def test_json_spinner(capsys):
    """
    Ensure that the JSONSpinner does not print anything to stdout
    """
    with JSONSpinner("Test"):
        pass

    capture = capsys.readouterr()

    assert capture.out == ""
