# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.common.serialize import json
from conda.plugins.reporter_backends.events import (
    DetailViewEvent,
    EnvsListEvent,
    FetchSectionEndEvent,
    FetchSectionStartEvent,
    FetchTaskEndEvent,
    FetchTaskProgressEvent,
    FetchTaskStartEvent,
    RenderDataEvent,
    SpinnerEndEvent,
    SpinnerStartEvent,
)
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

    with pytest.deprecated_call():
        assert json_handler_object.detail_view(test_data) == json.dumps(test_data)
    with pytest.deprecated_call():
        assert json_handler_object.envs_list(test_envs) == json.dumps(
            {"envs": test_envs}
        )
    with pytest.deprecated_call():
        assert json_handler_object.envs_list(test_envs_dict) == json.dumps(
            {"envs": test_envs}
        )
    with pytest.deprecated_call():
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


@pytest.mark.parametrize("data", ["a string", {"one": 1}, ["a", "b"], 3])
def test_handle_render_data_event(capsys, data):
    JSONReporterRenderer().handle(RenderDataEvent(data=data))

    assert capsys.readouterr().out == json.dumps(data)


def test_handle_detail_view_event_matches_legacy(capsys):
    data = {"one": "value_one", "two": 2, "three": True}
    renderer = JSONReporterRenderer()

    renderer.handle(DetailViewEvent(data=data))

    with pytest.deprecated_call():
        assert capsys.readouterr().out == renderer.detail_view(data)


def test_handle_envs_list_event_matches_legacy(capsys):
    prefixes = ("/envs/one", "/envs/two")
    renderer = JSONReporterRenderer()

    renderer.handle(EnvsListEvent(prefixes=prefixes))

    with pytest.deprecated_call():
        assert capsys.readouterr().out == renderer.envs_list(list(prefixes))


def test_handle_spinner_events_are_silent(capsys):
    renderer = JSONReporterRenderer()

    renderer.handle(SpinnerStartEvent(message="Solving"))
    renderer.handle(SpinnerEndEvent(message="Solving", success=True))

    assert capsys.readouterr().out == ""


def test_handle_fetch_events_match_legacy_progress_bar(mocker):
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    renderer = JSONReporterRenderer()

    renderer.handle(FetchSectionStartEvent())
    renderer.handle(
        FetchTaskStartEvent(task_id=1, name="numpy", version="1.0", size=2048)
    )
    renderer.handle(FetchTaskProgressEvent(task_id=1, fraction=0.3))
    renderer.handle(FetchTaskEndEvent(task_id=1, success=True))
    renderer.handle(FetchSectionEndEvent(success=True))

    legacy_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    with pytest.deprecated_call():
        bar = JSONReporterRenderer().progress_bar("numpy-1.0")
    bar.update_to(0.3)
    bar.finish()
    bar.refresh()
    bar.close()

    assert mock_stdout.write.mock_calls == legacy_stdout.write.mock_calls
    assert not renderer._fetch_bars


def test_handle_fetch_task_end_failure_does_not_finish_bar(mocker):
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    renderer = JSONReporterRenderer()
    renderer.handle(FetchTaskStartEvent(task_id=1, name="n", version="1"))

    renderer.handle(FetchTaskEndEvent(task_id=1, success=False))

    mock_stdout.write.assert_not_called()


def test_handle_fetch_events_for_unknown_task_are_ignored(mocker):
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    renderer = JSONReporterRenderer()

    renderer.handle(FetchTaskProgressEvent(task_id=9, fraction=1))
    renderer.handle(FetchTaskEndEvent(task_id=9, success=True))

    mock_stdout.write.assert_not_called()


def test_handle_fetch_task_start_without_name_has_empty_description(mocker):
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    renderer = JSONReporterRenderer()

    renderer.handle(FetchTaskStartEvent(task_id=1, name="", version=""))
    renderer.handle(FetchTaskProgressEvent(task_id=1, fraction=0.5))

    assert mock_stdout.write.mock_calls == [
        mocker.call(
            '{"fetch":"","finished":false,"maxval":1,"progress":0.500000}\n\x00'
        )
    ]
