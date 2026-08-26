# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from importlib import import_module
from typing import TYPE_CHECKING

import pytest

from conda.exceptions import CondaValueError
from conda.plugins import package_extractors, solvers

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from conda.plugins.manager import CondaPluginManager
    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


@pytest.fixture
def plugin_manager_with_plugins_command(
    plugin_manager_with_reporter_backends: CondaPluginManager,
) -> CondaPluginManager:
    plugin_manager_with_reporter_backends.load_plugins(
        *package_extractors.plugins,
        solvers,
        import_module("conda.plugins.subcommands.plugins"),
    )
    return plugin_manager_with_reporter_backends


@pytest.fixture
def plugin_manager_with_test_plugin(
    plugin_manager_with_plugins_command: CondaPluginManager,
) -> CondaPluginManager:
    assert (
        plugin_manager_with_plugins_command.load_entrypoints(
            "test_plugin",
            "success",
        )
        == 1
    )
    return plugin_manager_with_plugins_command


def test_plugins_help(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli("plugins", "--help", raises=SystemExit)

    assert exc.value.code == 0
    assert "info" in out
    assert "install" in out
    assert "list" in out
    assert "remove" in out
    assert "update" in out
    assert not err


def test_plugins_info_help(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli("plugins", "info", "--help", raises=SystemExit)

    assert exc.value.code == 0
    assert "Show detailed information about an installed conda plugin." in out
    assert "NAME" in out
    assert not err


def test_plugins_install_help(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli("plugins", "install", "--help", raises=SystemExit)

    assert exc.value.code == 0
    assert "Install conda plugin packages into an environment." in out
    assert "package_spec" in out
    assert "--all" not in out
    assert not err


def test_plugins_list_help(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli("plugins", "list", "--help", raises=SystemExit)

    assert exc.value.code == 0
    assert "List installed conda plugins." in out
    assert not err


def test_plugins_remove_help(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli("plugins", "remove", "--help", raises=SystemExit)

    assert exc.value.code == 0
    assert "Remove conda plugin packages from an environment." in out
    assert "package_name" in out
    assert "--all" not in out
    assert not err


def test_plugins_update_help(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli("plugins", "update", "--help", raises=SystemExit)

    assert exc.value.code == 0
    assert "Update conda plugin packages in an environment." in out
    assert "--all" in out
    assert "package_spec" in out
    assert not err


def test_plugins_list_empty(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, code = conda_cli("plugins", "list")

    assert code == 0, f"conda plugins list failed ({code}): {err}"
    assert out == "No plugins installed.\n"
    assert not err


def test_plugins_install_delegates_to_conda_install(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    install_module = import_module("conda.plugins.subcommands.plugins.install")
    execute = mocker.patch.object(
        install_module.main_install, "execute", return_value=0
    )

    out, err, code = conda_cli("plugins", "install", "conda-example-plugin")

    assert code == 0, f"conda plugins install failed ({code}): {err}"
    args, parser = execute.call_args.args
    assert args.cmd == "install"
    assert args.packages == ["conda-example-plugin"]
    assert args.revision is None
    assert (
        args._validate_explicit_packages
        is install_module.require_explicit_plugin_packages
    )
    assert (
        args._validate_transaction.func
        is install_module.require_plugin_install_transaction
    )
    assert args._validate_transaction.keywords == {"prefetch_link_precs": True}
    assert not hasattr(args, "_validate_prepared_transaction")
    assert parser.prog.endswith("plugins install")
    assert not out
    assert not err


@pytest.mark.parametrize(
    "prefetch_link_precs",
    (False, True),
    ids=("installed", "prefetched"),
)
def test_plugins_install_validation_rejects_non_plugin(
    prefetch_link_precs: bool,
    plugin_manager_with_plugins_command: CondaPluginManager,
    mocker: MockerFixture,
):
    package_validation = import_module(
        "conda.plugins.subcommands.plugins.package_validation"
    )
    from conda.core.link import PrefixSetup, UnlinkLinkTransaction
    from conda.models.match_spec import MatchSpec
    from conda.models.records import PackageRecord

    record = PackageRecord(
        name="numpy",
        version="1.0",
        build="0",
        build_number=0,
        channel="test",
        subdir="noarch",
        fn="numpy-1.0-0.tar.bz2",
    )
    prefix_data = mocker.Mock()
    prefix_data.get.return_value = record
    mocker.patch.object(package_validation, "PrefixData", return_value=prefix_data)
    mocker.patch.object(
        plugin_manager_with_plugins_command,
        "is_conda_plugin_package",
        return_value=False,
    )
    if prefetch_link_precs:
        progressive_fetch_extract = mocker.patch.object(
            package_validation,
            "ProgressiveFetchExtract",
        )
        mocker.patch.object(
            package_validation.PackageCacheData,
            "get_entry_to_link",
            return_value=mocker.sentinel.package_cache_record,
        )
        mocker.patch.object(
            package_validation,
            "read_package_info",
            return_value=mocker.sentinel.package_info,
        )

    transaction = UnlinkLinkTransaction(
        PrefixSetup(
            "/prefix",
            (),
            (record,) if prefetch_link_precs else (),
            (),
            (MatchSpec("numpy"),),
            (),
        )
    )

    with pytest.raises(CondaValueError) as exc:
        package_validation.require_plugin_install_transaction(
            transaction,
            prefetch_link_precs=prefetch_link_precs,
        )

    assert "`conda plugins install` can only install conda plugin packages" in str(exc)
    assert "numpy" in str(exc)
    if prefetch_link_precs:
        progressive_fetch_extract.assert_called_once_with((record,))
        progressive_fetch_extract.return_value.execute.assert_called_once_with()


def test_install_handle_txn_runs_validation_before_confirmation(
    mocker: MockerFixture,
):
    from argparse import Namespace

    from conda.cli.install import handle_txn

    calls = []
    transaction = mocker.Mock()
    transaction.nothing_to_do = False
    transaction.print_transaction_summary.side_effect = lambda: calls.append("summary")
    transaction.download_and_extract.side_effect = lambda: calls.append("download")
    transaction.execute.side_effect = lambda: calls.append("execute")
    validator = mocker.Mock(side_effect=lambda transaction: calls.append("validate"))
    args = Namespace(_validate_transaction=validator)
    mocker.patch(
        "conda.cli.install.confirm_yn",
        side_effect=lambda: calls.append("confirm"),
    )

    handle_txn(transaction, "/prefix", args, newenv=False)

    assert calls == ["validate", "summary", "confirm", "download", "execute"]
    validator.assert_called_once_with(transaction)


def test_plugins_install_rejects_before_fetching_dependencies(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    tmp_pkgs_dir: Path,
    mocker: MockerFixture,
):
    from conda.core.prefix_data import PrefixData

    confirm = mocker.patch("conda.cli.install.confirm_yn")
    with tmp_env(shallow=True) as prefix:
        out, _, exc = conda_cli(
            "plugins",
            "install",
            f"--prefix={prefix}",
            "--solver=classic",
            "dependent=1.0",
            raises=CondaValueError,
        )

        assert PrefixData(prefix).get("dependent", None) is None
        assert PrefixData(prefix).get("dependency", None) is None

    confirm.assert_not_called()
    assert "Package Plan" not in out
    assert "Not conda plugin packages: dependent=1.0" in str(exc.value)
    assert (tmp_pkgs_dir / "dependent-1.0-0.conda").is_file()
    assert (tmp_pkgs_dir / "dependent-1.0-0").is_dir()
    assert not (tmp_pkgs_dir / "dependency-1.0-0.conda").exists()
    assert not (tmp_pkgs_dir / "dependency-1.0-0").exists()


def test_plugins_install_dry_run_does_not_prefetch(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    tmp_pkgs_dir: Path,
):
    from conda.exceptions import DryRunExit

    with tmp_env(shallow=True) as prefix:
        conda_cli(
            "plugins",
            "install",
            f"--prefix={prefix}",
            "--dry-run",
            "--solver=classic",
            "dependent=1.0",
            raises=DryRunExit,
        )

    assert not (tmp_pkgs_dir / "dependent-1.0-0.conda").exists()
    assert not (tmp_pkgs_dir / "dependent-1.0-0").exists()
    assert not (tmp_pkgs_dir / "dependency-1.0-0.conda").exists()
    assert not (tmp_pkgs_dir / "dependency-1.0-0").exists()


def test_plugins_info(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, code = conda_cli("plugins", "info", "conda-test-plugin")

    assert code == 0, f"conda plugins info failed ({code}): {err}"
    assert "Name" in out
    assert "conda-test-plugin" in out
    assert "Version" in out
    assert "1.0" in out
    assert "Status" in out
    assert "active" in out
    assert "Canonical name" in out
    assert "test_plugin.success" in out
    assert "Hooks" in out
    assert "solvers" in out
    assert "Summary" in out
    assert "A test plugin" in out
    assert "Homepage      : https://example.com/legacy-home" in out
    assert "Project URLs  :\n" in out
    assert "  - Home: https://example.com/home" in out
    assert "  - Documentation: https://example.com/docs" in out
    assert not err


def test_plugins_info_json(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, code = conda_cli("plugins", "info", "test_plugin.success", "--json")

    assert code == 0, f"conda plugins info --json failed ({code}): {err}"
    assert json.loads(out) == {
        "name": "conda-test-plugin",
        "version": "1.0",
        "canonical_name": "test_plugin.success",
        "status": "active",
        "hooks": ["solvers"],
        "summary": "A test plugin",
        "license": "",
        "homepage": "https://example.com/legacy-home",
        "project_urls": [
            {"label": "Home", "url": "https://example.com/home"},
            {"label": "Documentation", "url": "https://example.com/docs"},
        ],
    }
    assert not err


def test_plugins_info_not_found(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli(
        "plugins",
        "info",
        "missing",
        raises=CondaValueError,
    )

    assert "No installed conda plugin found matching 'missing'." in str(exc)
    assert not out
    assert not err


def test_plugins_remove_delegates_to_conda_remove(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    remove_module = import_module("conda.plugins.subcommands.plugins.remove")
    execute = mocker.patch.object(remove_module.main_remove, "execute", return_value=0)

    out, err, code = conda_cli("plugins", "remove", "conda-test-plugin")

    assert code == 0, f"conda plugins remove failed ({code}): {err}"
    args, parser = execute.call_args.args
    assert args.cmd == "remove"
    assert args.package_names == ["conda-test-plugin"]
    assert args.all is False
    assert args.features is False
    assert parser.prog.endswith("plugins remove")
    assert not out
    assert not err


def test_plugins_remove_rejects_non_plugin_package(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli(
        "plugins",
        "remove",
        "numpy",
        raises=CondaValueError,
    )

    assert (
        "`conda plugins remove` can only operate on installed conda plugin packages"
        in str(exc)
    )
    assert "numpy" in str(exc)
    assert not out
    assert not err


def test_plugins_update_delegates_to_conda_update(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    update_module = import_module("conda.plugins.subcommands.plugins.update")
    execute = mocker.patch.object(update_module.main_update, "execute", return_value=0)

    out, err, code = conda_cli("plugins", "update", "conda-test-plugin")

    assert code == 0, f"conda plugins update failed ({code}): {err}"
    args, parser = execute.call_args.args
    assert args.cmd == "update"
    assert args.packages == ["conda-test-plugin"]
    assert args.update_all_plugins is False
    assert parser.prog.endswith("plugins update")
    assert not out
    assert not err


def test_plugins_update_rejects_non_plugin_package(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli(
        "plugins",
        "update",
        "numpy",
        raises=CondaValueError,
    )

    assert (
        "`conda plugins update` can only operate on installed conda plugin packages"
        in str(exc)
    )
    assert "numpy" in str(exc)
    assert not out
    assert not err


def test_plugins_update_all_uses_installed_plugin_packages(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    update_module = import_module("conda.plugins.subcommands.plugins.update")
    execute = mocker.patch.object(update_module.main_update, "execute", return_value=0)

    out, err, code = conda_cli("plugins", "update", "--all")

    assert code == 0, f"conda plugins update --all failed ({code}): {err}"
    args, parser = execute.call_args.args
    assert args.cmd == "update"
    assert args.packages == ["conda-test-plugin"]
    assert args.update_all_plugins is True
    assert parser.prog.endswith("plugins update")
    assert not out
    assert not err


def test_plugins_update_all_rejects_package_names(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli(
        "plugins",
        "update",
        "--all",
        "conda-example-plugin",
        raises=CondaValueError,
    )

    assert "cannot combine --all with plugin package names or --file" in str(exc)
    assert not out
    assert not err


def test_plugins_update_all_without_plugins(
    plugin_manager_with_plugins_command: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, exc = conda_cli(
        "plugins",
        "update",
        "--all",
        raises=CondaValueError,
    )

    assert "No installed conda plugins found to update." in str(exc)
    assert not out
    assert not err


def test_plugins_list_table(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, code = conda_cli("plugins", "list")

    assert code == 0, f"conda plugins list failed ({code}): {err}"
    assert "Name" in out
    assert "Version" in out
    assert "Status" in out
    assert "Hooks" in out
    assert "conda-test-plugin" in out
    assert "active" in out
    assert "solvers" in out
    assert not err


def test_plugins_list_disabled(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("CONDA_NO_PLUGINS", "true")

    out, err, code = conda_cli("plugins", "list")

    assert code == 0, f"conda plugins list failed ({code}): {err}"
    assert "conda-test-plugin" in out
    assert "disabled" in out
    assert "solvers" in out
    assert not err


def test_plugins_list_json(
    plugin_manager_with_test_plugin: CondaPluginManager,
    conda_cli: CondaCLIFixture,
):
    out, err, code = conda_cli("plugins", "list", "--json")

    assert code == 0, f"conda plugins list --json failed ({code}): {err}"
    data = json.loads(out)
    test_plugin = next(
        plugin for plugin in data if plugin["name"] == "conda-test-plugin"
    )

    assert test_plugin == {
        "name": "conda-test-plugin",
        "version": "1.0",
        "canonical_name": "test_plugin.success",
        "status": "active",
        "hooks": ["solvers"],
    }
    assert not err
