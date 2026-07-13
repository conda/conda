# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
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


# ---------------------------------------------------------------------------
# render_* event method tests
# ---------------------------------------------------------------------------


def test_render_data(mocker):
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    renderer = JSONReporterRenderer()
    renderer.render_data(RenderDataEvent(data={"key": "val"}))
    mock_stdout.write.assert_called_once_with(json.dumps({"key": "val"}))


def test_render_detail_view(mocker):
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    renderer = JSONReporterRenderer()
    data = {"a": 1}
    renderer.render_detail_view(DetailViewEvent(data=data))
    mock_stdout.write.assert_called_once_with(json.dumps(data))


def test_render_envs_list(mocker):
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    renderer = JSONReporterRenderer()
    renderer.render_envs_list(EnvsListEvent(prefixes=("/env1", "/env2")))
    mock_stdout.write.assert_called_once_with(json.dumps({"envs": ["/env1", "/env2"]}))


def test_render_spinner_start_silent(capsys):
    renderer = JSONReporterRenderer()
    renderer.render_spinner_start(SpinnerStartEvent(message="msg"))
    out, _ = capsys.readouterr()
    assert out == ""


def test_render_spinner_end_silent(capsys):
    renderer = JSONReporterRenderer()
    renderer.render_spinner_end(SpinnerEndEvent(message="msg", success=True))
    out, _ = capsys.readouterr()
    assert out == ""


def test_render_fetch_section_start_clears_tasks():
    renderer = JSONReporterRenderer()
    renderer._fetch_tasks[1] = "old"
    renderer.render_fetch_section_start(FetchSectionStartEvent())
    assert renderer._fetch_tasks == {}


def test_render_fetch_task_start_registers_task():
    renderer = JSONReporterRenderer()
    renderer.render_fetch_section_start(FetchSectionStartEvent())
    renderer.render_fetch_task_start(
        FetchTaskStartEvent(task_id=42, name="numpy", version="1.26", size=None)
    )
    assert 42 in renderer._fetch_tasks
    assert "numpy" in renderer._fetch_tasks[42]


def test_render_fetch_task_progress(mocker):
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    renderer = JSONReporterRenderer()
    renderer._fetch_tasks[7] = "pkg-1.0"
    renderer.render_fetch_task_progress(FetchTaskProgressEvent(task_id=7, fraction=0.5))
    written = mock_stdout.write.call_args[0][0]
    assert '"finished":false' in written
    assert "0.500000" in written


def test_render_fetch_task_end_writes_finished(mocker):
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    renderer = JSONReporterRenderer()
    renderer._fetch_tasks[8] = "pkg-2.0"
    renderer.render_fetch_task_end(FetchTaskEndEvent(task_id=8, success=True))
    written = mock_stdout.write.call_args[0][0]
    assert '"finished":true' in written
    assert 8 not in renderer._fetch_tasks


def test_render_fetch_task_end_failure_no_output(mocker):
    mock_stdout = mocker.patch("conda.plugins.reporter_backends.json.sys.stdout")
    renderer = JSONReporterRenderer()
    renderer._fetch_tasks[9] = "pkg-3.0"
    renderer.render_fetch_task_end(FetchTaskEndEvent(task_id=9, success=False))
    mock_stdout.write.assert_not_called()


def test_render_fetch_section_end_clears_tasks():
    renderer = JSONReporterRenderer()
    renderer._fetch_tasks[1] = "pkg"
    renderer.render_fetch_section_end(FetchSectionEndEvent(success=True))
    assert renderer._fetch_tasks == {}
