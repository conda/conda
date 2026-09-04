# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.cli.formats import get_multiplatform_lockfile
from conda.plugins.types import CondaEnvironmentExporter, EnvironmentFormat


def test_get_multiplatform_lockfile():
    # no plugins
    assert get_multiplatform_lockfile({}) is None
    assert get_multiplatform_lockfile({EnvironmentFormat.environment: []}) is None
    assert get_multiplatform_lockfile({EnvironmentFormat.lockfile: []}) is None

    # no multiplatform export
    single_lock = CondaEnvironmentExporter(
        name="dummy-single-lock",
        aliases=("single-lock",),
        default_filenames=("single.dummy",),
        export=lambda envs: "",
        environment_format=EnvironmentFormat.lockfile,
    )
    lockfile = get_multiplatform_lockfile({EnvironmentFormat.lockfile: [single_lock]})
    assert lockfile is None

    # no default filenames
    ignored_lock = CondaEnvironmentExporter(
        name="dummy-ignored-lock",
        aliases=("ignored-lock",),
        default_filenames=(),
        multiplatform_export=lambda envs: "",
        environment_format=EnvironmentFormat.lockfile,
    )
    lockfile = get_multiplatform_lockfile({EnvironmentFormat.lockfile: [ignored_lock]})
    assert lockfile is None

    # return first default filename
    multi_lock = CondaEnvironmentExporter(
        name="dummy-multi-lock",
        aliases=("multi-lock",),
        default_filenames=("multi.dummy", "multi.other"),
        multiplatform_export=lambda envs: "",
        environment_format=EnvironmentFormat.lockfile,
    )
    lockfile = get_multiplatform_lockfile(
        {EnvironmentFormat.lockfile: [ignored_lock, multi_lock]}
    )
    assert lockfile == "multi.dummy"
