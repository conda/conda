# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import shutil
from argparse import Namespace
from pathlib import Path

import pytest
from conda.base.constants import SEARCH_PATH
from conda.base.context import Context


@pytest.fixture
def config_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("CONDA_NOTIFY_OUTDATED_CONDA", raising=False)
    root = tmp_path / "runtime"
    user = tmp_path / "user"
    root.mkdir()
    user.mkdir()
    return root, user


def configured_context(root: Path, user: Path) -> Context:
    locations = {
        "$CONDA_ROOT": root,
        "$XDG_CONFIG_HOME": user / ".config",
        "~": user,
        "$CONDA_PREFIX": root,
        "$CONDARC": user / "explicit.yaml",
    }
    # Keep conda's real search order, including duplicate root/target paths,
    # while excluding host configuration and using only temporary directories.
    search_path = tuple(
        Path(template.replace(variable, str(location), 1))
        for template in SEARCH_PATH
        for variable, location in locations.items()
        if template.startswith(variable)
    )
    return Context(search_path=search_path, argparse_args=Namespace(prefix=str(root)))


def install_notification_defaults(root: Path) -> Path:
    source = Path(__file__).parents[1] / "condarc.d" / "conda-runtime-updater.yaml"
    destination = root / "condarc.d" / source.name
    destination.parent.mkdir()
    shutil.copyfile(source, destination)
    return destination


@pytest.mark.parametrize("existing_config", [False, True], ids=["fresh", "existing"])
def test_packaged_default_preserves_root_config_and_removal_restores_stock_default(
    config_paths, existing_config
):
    root, user = config_paths
    condarc = root / ".condarc"
    original = b"# Keep the installation's channel settings.\nchannels:\n  - conda-forge\n"
    if existing_config:
        condarc.write_bytes(original)
    assert configured_context(root, user).notify_outdated_conda is True

    drop_in = install_notification_defaults(root)

    assert configured_context(root, user).notify_outdated_conda is False
    if existing_config:
        assert condarc.read_bytes() == original
    else:
        assert not condarc.exists()

    drop_in.unlink()

    assert configured_context(root, user).notify_outdated_conda is True
    if existing_config:
        assert condarc.read_bytes() == original
    else:
        assert not condarc.exists()


def test_user_config_can_restore_stock_notification(config_paths):
    root, user = config_paths
    drop_in = install_notification_defaults(root)
    packaged = drop_in.read_bytes()
    user_config = user / ".condarc"
    original = b"# Explicit user preference.\nnotify_outdated_conda: true\n"
    user_config.write_bytes(original)

    assert configured_context(root, user).notify_outdated_conda is True
    assert user_config.read_bytes() == original
    assert drop_in.read_bytes() == packaged


def test_environment_can_restore_stock_notification(config_paths, monkeypatch):
    root, user = config_paths
    install_notification_defaults(root)
    (user / ".condarc").write_text("notify_outdated_conda: false\n", encoding="utf-8")
    monkeypatch.setenv("CONDA_NOTIFY_OUTDATED_CONDA", "true")

    assert configured_context(root, user).notify_outdated_conda is True


def test_registered_notification_setting_loads_user_preference(config_paths, monkeypatch):
    root, user = config_paths
    monkeypatch.delenv("CONDA_PLUGINS_RUNTIME_UPDATE_NOTIFICATIONS", raising=False)
    defaults = configured_context(root, user)

    assert "runtime_update_notifications" in defaults.plugin_manager.get_settings()
    assert defaults.plugins.runtime_update_notifications is True

    (user / ".condarc").write_text(
        "plugins:\n  runtime_update_notifications: false\n", encoding="utf-8"
    )

    assert configured_context(root, user).plugins.runtime_update_notifications is False
