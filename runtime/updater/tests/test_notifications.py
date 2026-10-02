# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from types import SimpleNamespace

import pytest
from conda.exceptions import CondaError

from conda_runtime_updater import helper, notifications, plugin
from conda_runtime_updater.metadata import RuntimeMetadata


@pytest.fixture
def runtime(tmp_path):
    return RuntimeMetadata(
        prefix=tmp_path,
        path=tmp_path / ".conda.json",
        version="26.9.0",
        executable=tmp_path / "conda",
        lock_path=tmp_path / ".conda.update.lock",
        ownership="direct",
        instruction=None,
    )


@pytest.fixture
def probe_response(runtime):
    return {
        "available": True,
        "current_version": runtime.version,
        "current_build_number": 0,
        "version": "26.9.0.post1",
        "build_number": 1,
        "package": "conda-runtime",
        "sha256": "a" * 64,
        "ownership": runtime.ownership,
        "installation": None,
        "instruction": None,
        "source": "network",
        "cache_age_seconds": None,
    }


@pytest.fixture
def notice_environment(monkeypatch, tmp_path, runtime, probe_response, capsys):
    context = SimpleNamespace(
        root_prefix=str(runtime.prefix),
        offline=False,
        quiet=False,
        json=False,
        dry_run=False,
        plugins=SimpleNamespace(runtime_update_notifications=True),
    )
    calls = []
    clock = [200_000.0]

    def probe(_runtime, *, offline):
        calls.append(offline)
        return probe_response

    monkeypatch.setattr(notifications, "context", context)
    monkeypatch.setattr(notifications, "discover_runtime", lambda _prefix: runtime)
    monkeypatch.setattr(notifications, "probe_runtime", probe)
    monkeypatch.setattr(notifications, "user_cache_dir", lambda *_args: str(tmp_path / "cache"))
    monkeypatch.setattr(notifications, "time", lambda: clock[0])
    stream_types = {
        type(notifications.sys.stdin),
        type(notifications.sys.stdout),
        type(notifications.sys.stderr),
    }
    for stream_type in stream_types:
        monkeypatch.setattr(stream_type, "isatty", lambda _self: True)
    return context, calls, clock


@pytest.mark.parametrize(
    "flag", ["quiet", "json", "dry_run", "disabled", "stdin", "stdout", "stderr"]
)
def test_ineligible_commands_do_not_probe_or_write_state(
    monkeypatch, tmp_path, notice_environment, flag, capsys
):
    context, calls, _clock = notice_environment
    if flag == "disabled":
        context.plugins.runtime_update_notifications = False
    elif flag in {"stdin", "stdout", "stderr"}:
        monkeypatch.setattr(getattr(notifications.sys, flag), "isatty", lambda: False)
    else:
        setattr(context, flag, True)

    notifications.notify("list")

    assert calls == []
    assert not (tmp_path / "cache").exists()
    assert capsys.readouterr() == ("", "")


def test_unmanaged_conda_is_silent(monkeypatch, notice_environment, capsys):
    _context, calls, _clock = notice_environment
    monkeypatch.setattr(notifications, "discover_runtime", lambda _prefix: None)
    notifications.notify("list")
    assert calls == []
    assert capsys.readouterr() == ("", "")


def test_daily_probe_uses_rust_cache_and_deduplicates_notices(notice_environment, capsys):
    _context, calls, clock = notice_environment
    notifications.notify("list")
    output = capsys.readouterr()
    assert output.out == ""
    assert "26.9.0.post1" in output.err
    assert "build 1" in output.err
    assert "conda self update" in output.err

    notifications.notify("info")
    assert calls == [False, True]
    assert capsys.readouterr() == ("", "")

    clock[0] += 86_400
    notifications.notify("list")
    assert calls == [False, True, False]
    assert "conda self update" in capsys.readouterr().err


@pytest.mark.parametrize(("age", "description"), [(172_800, "2 days"), (None, "age unknown")])
def test_offline_notice_uses_cached_age_without_delaying_reconnect(
    notice_environment, probe_response, capsys, age, description
):
    context, calls, _clock = notice_environment
    context.offline = True
    probe_response.update(source="cache", cache_age_seconds=age)
    notifications.notify("list")
    assert calls == [True]
    output = capsys.readouterr()
    assert output.out == ""
    assert "Cached channel metadata" in output.err
    assert description in output.err

    context.offline = False
    probe_response.update(source="network", cache_age_seconds=None)
    notifications.notify("info")
    assert calls == [True, False]
    assert capsys.readouterr() == ("", "")


def test_new_build_candidate_is_not_suppressed_by_previous_notice(
    notice_environment, probe_response, capsys
):
    notifications.notify("list")
    capsys.readouterr()
    probe_response.update(version="26.9.0", build_number=2, sha256="b" * 64)
    notifications.notify("list")
    assert "26.9.0 (build 2)" in capsys.readouterr().err


def test_external_runtime_uses_recorded_instruction(
    monkeypatch, runtime, notice_environment, probe_response, capsys
):
    external = replace(runtime, ownership="external", instruction="brew upgrade conda")
    monkeypatch.setattr(notifications, "discover_runtime", lambda _prefix: external)
    probe_response.update(ownership="external", instruction="brew upgrade conda")
    notifications.notify("list")
    output = capsys.readouterr()
    assert "brew upgrade conda" in output.err
    assert "conda self update" not in output.err


@pytest.mark.parametrize("response", [None, {"available": None}, {"available": False}])
def test_unknown_or_current_runtime_is_silent_but_online_attempt_is_throttled(
    monkeypatch, notice_environment, response, capsys
):
    _context, calls, _clock = notice_environment

    def probe(_runtime, *, offline):
        calls.append(offline)
        return response

    monkeypatch.setattr(notifications, "probe_runtime", probe)
    notifications.notify("list")
    notifications.notify("list")
    assert calls == [False, True]
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "contents", ["not json", "[]", '{"checked_at":300000}', '{"checked_at":true}']
)
def test_invalid_or_future_throttle_state_does_not_block_check(
    tmp_path, runtime, notice_environment, contents
):
    path = notifications.cache_path(runtime)
    path.parent.mkdir(parents=True)
    path.write_text(contents)
    notifications.notify("list")
    assert notice_environment[1] == [False]
    assert isinstance(json.loads(path.read_text()), dict)


def test_unwritable_cache_does_not_fail_command(tmp_path, notice_environment, capsys):
    (tmp_path / "cache").write_text("not a directory")
    notifications.notify("list")
    assert "conda self update" in capsys.readouterr().err


def test_probe_invocation_has_short_deadline_and_preserves_effective_offline(
    monkeypatch, runtime, probe_response
):
    monkeypatch.setattr(helper, "context", SimpleNamespace(offline=True))
    monkeypatch.setenv(helper.CANDIDATE_ENV, "inherited candidate")
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, json.dumps(probe_response), "")

    monkeypatch.setattr(helper.subprocess, "run", run)
    assert helper.probe_runtime(runtime, offline=False) == probe_response
    argv, kwargs = calls[0]
    assert argv == [runtime.executable]
    assert kwargs["timeout"] == 5
    assert kwargs["env"][helper.ACTION_ENV] == "v1/probe"
    assert kwargs["env"][helper.OFFLINE_ENV] == "1"
    assert helper.CANDIDATE_ENV not in kwargs["env"]


@pytest.mark.parametrize(
    "result",
    [
        subprocess.CompletedProcess([], 1, "", "unknown internal runtime update action: v1/probe"),
        subprocess.CompletedProcess([], 0, "invalid json", ""),
        subprocess.CompletedProcess([], 0, "[]", ""),
        subprocess.CompletedProcess([], 0, '{"available":true}', ""),
        subprocess.TimeoutExpired([], 5),
        OSError("cannot execute"),
    ],
)
def test_probe_failures_are_silent(monkeypatch, runtime, result):
    monkeypatch.setattr(helper, "context", SimpleNamespace(offline=False))

    def run(*_args, **_kwargs):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(helper.subprocess, "run", run)
    assert helper.probe_runtime(runtime, offline=False) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("available", "yes"),
        ("source", "untrusted"),
        ("source", []),
        ("source", {}),
        ("current_version", "26.7.2"),
        ("current_build_number", True),
        ("build_number", -1),
        ("sha256", "invalid"),
        ("version", "26.9.0\nmisleading output"),
        ("cache_age_seconds", True),
        ("ownership", "external"),
    ],
)
def test_probe_rejects_malformed_notice_data(runtime, probe_response, field, value):
    probe_response[field] = value
    if field == "cache_age_seconds":
        probe_response["source"] = "cache"
    with pytest.raises(CondaError):
        helper.validate_probe(probe_response, runtime)


def test_post_command_notifies_only_without_a_staged_update(monkeypatch):
    calls = []
    monkeypatch.setattr(plugin, "notify", calls.append)
    monkeypatch.setattr(plugin, "_session", None)
    plugin.post_command("list")
    assert calls == ["list"]
