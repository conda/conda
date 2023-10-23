# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Collection of helper functions used in conda tests."""
import json
import os
import re
import sys
from contextlib import contextmanager
from functools import lru_cache
from os.path import abspath, dirname, join
from pathlib import Path
from tempfile import gettempdir, mkdtemp
from unittest.mock import patch
from uuid import uuid4

import pytest

from conda.auxlib.compat import shlex_split_unicode
from conda.deprecations import deprecated
from conda_env.cli import main as conda_env_cli

from .. import cli
from ..base.context import conda_tests_ctxt_mgmt_def_pol, context, reset_context
from ..common.compat import encode_arguments
from ..common.io import argv, env_var
from ..common.io import captured as common_io_captured
from ..core.prefix_data import PrefixData
from ..core.subdir_data import SubdirData, make_feature_record
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.read import lexists
from ..gateways.logging import initialize_logging
from ..history import History
from ..models.channel import Channel
from ..models.records import PackageRecord, PrefixRecord
from ..resolve import Resolve

# The default value will only work if we have installed conda in development mode!
TEST_DATA_DIR = os.environ.get(
    "CONDA_TEST_DATA_DIR", abspath(join(dirname(__file__), "..", "..", "tests", "data"))
)
CHANNEL_DIR = abspath(join(TEST_DATA_DIR, "conda_format_repo"))
EXPORTED_CHANNELS_DIR = mkdtemp(suffix="-test-conda-channels")


expected_error_prefix = "Using Anaconda Cloud api site https://api.anaconda.org"


def strip_expected(stderr):
    if expected_error_prefix and stderr.startswith(expected_error_prefix):
        stderr = stderr[len(expected_error_prefix) :].lstrip()  # noqa
    return stderr


def raises(exception, func, string=None):
    try:
        a = func()
    except exception as e:
        if string:
            assert string in e.args[0]
        print(e)
        return True
    raise Exception("did not raise, gave %s" % a)


@contextmanager
def captured(disallow_stderr=True):
    # same as common.io.captured but raises Exception if unexpected output was written to stderr
    try:
        with common_io_captured() as c:
            yield c
    finally:
        c.stderr = strip_expected(c.stderr)
        if disallow_stderr and c.stderr:
            raise Exception("Got stderr output: %s" % c.stderr)


def capture_json_with_argv(
    command, disallow_stderr=True, ignore_stderr=False, **kwargs
):
    stdout, stderr, exit_code = run_inprocess_conda_command(command, disallow_stderr)
    if kwargs.get("relaxed"):
        match = re.match(r"\A.*?({.*})", stdout, re.DOTALL)
        if match:
            stdout = match.groups()[0]
    elif stderr and not ignore_stderr:
        # TODO should be exception
        return stderr
    try:
        return json.loads(stdout.strip())
    except ValueError:
        raise


@deprecated(
    "24.3",
    "24.9",
    addendum="Use `mocker.patch('conda.base.context.Context.active_prefix')` instead.",
)
@contextmanager
def set_active_prefix(prefix: str) -> None:
    old_prefix = os.environ["CONDA_PREFIX"]

    try:
        os.environ["CONDA_PREFIX"] = prefix
        yield
    finally:
        os.environ["CONDA_PREFIX"] = old_prefix


def assert_equals(a, b, output=""):
    output = f"{a.lower()!r} != {b.lower()!r}" + "\n\n" + output
    assert a.lower() == b.lower(), output


def assert_not_in(a, b, output=""):
    assert a.lower() not in b.lower(), "{} {!r} should not be found in {!r}".format(
        output,
        a.lower(),
        b.lower(),
    )


def assert_in(a, b, output=""):
    assert a.lower() in b.lower(), "{} {!r} cannot be found in {!r}".format(
        output, a.lower(), b.lower()
    )


@deprecated("23.9", "24.3", addendum="Use `conda.testing.conda_cli` instead.")
def run_inprocess_conda_command(command, disallow_stderr: bool = True):
    # anything that uses this function is an integration test
    reset_context(())

    # determine whether this is a conda_env command and assign appropriate main function
    if command.startswith("conda env"):
        command = command.replace("env", "")  # Remove 'env' because of command parser
        main_func = conda_env_cli.main
    else:
        main_func = cli.main

    # May want to do this to command:
    with argv(encode_arguments(shlex_split_unicode(command))), captured(
        disallow_stderr
    ) as c:
        initialize_logging()
        try:
            exit_code = main_func()
        except SystemExit:
            pass
    print(c.stderr, file=sys.stderr)
    print(c.stdout)
    return c.stdout, c.stderr, exit_code


def add_subdir(dist_string):
    channel_str, package_str = dist_string.split("::")
    channel_str = channel_str + "/" + context.subdir
    return "::".join([channel_str, package_str])


def add_subdir_to_iter(iterable):
    if isinstance(iterable, dict):
        return {add_subdir(k): v for k, v in iterable.items()}
    elif isinstance(iterable, list):
        return list(map(add_subdir, iterable))
    elif isinstance(iterable, set):
        return set(map(add_subdir, iterable))
    elif isinstance(iterable, tuple):
        return tuple(map(add_subdir, iterable))
    else:
        raise Exception("Unable to add subdir to object of unknown type.")


@contextmanager
def tempdir():
    tempdirdir = gettempdir()
    dirname = str(uuid4())[:8]
    prefix = join(tempdirdir, dirname)
    try:
        os.makedirs(prefix)
        yield prefix
    finally:
        if lexists(prefix):
            rm_rf(prefix)


def supplement_index_with_repodata(index, repodata, channel, priority):
    repodata_info = repodata["info"]
    arch = repodata_info.get("arch")
    platform = repodata_info.get("platform")
    subdir = repodata_info.get("subdir")
    if not subdir:
        subdir = "{}-{}".format(repodata_info["platform"], repodata_info["arch"])
    auth = channel.auth
    for fn, info in repodata["packages"].items():
        rec = PackageRecord.from_objects(
            info,
            fn=fn,
            arch=arch,
            platform=platform,
            channel=channel,
            subdir=subdir,
            # schannel=schannel,
            priority=priority,
            # url=join_url(channel_url, fn),
            auth=auth,
        )
        index[rec] = rec


def add_feature_records_legacy(index):
    all_features = set()
    for rec in index.values():
        if rec.track_features:
            all_features.update(rec.track_features)

    for feature_name in all_features:
        rec = make_feature_record(feature_name)
        index[rec] = rec


def _export_subdir_data_to_repodata(subdir_data, index):
    """
    This function is only temporary and meant to patch wrong / undesirable
    testing behaviour. It should end up being replaced with the new class-based,
    backend-agnostic solver tests.
    """
    state = subdir_data._internal_state
    packages = {}
    for pkg in index:
        data = pkg.dump()
        if pkg.timestamp:
            data["timestamp"] = pkg.timestamp
        if "features" in data:
            # Features are deprecated, so they are not implemented
            # in modern solvers like mamba. Mamba does implement
            # track_features minimization, so we are exposing the
            # features as track_features, which seems to make the
            # tests pass
            data["track_features"] = data["features"]
            del data["features"]
        packages[pkg.fn] = data
    return {
        "_cache_control": state["_cache_control"],
        "_etag": state["_etag"],
        "_mod": state["_mod"],
        "_url": state["_url"],
        "_add_pip": state["_add_pip"],
        "info": {
            "subdir": context.subdir,
        },
        "packages": packages,
    }


def _sync_channel_to_disk(channel, subdir_data, index):
    """
    This function is only temporary and meant to patch wrong / undesirable
    testing behaviour. It should end up being replaced with the new class-based,
    backend-agnostic solver tests.
    """
    base = Path(EXPORTED_CHANNELS_DIR) / channel.name
    subdir = base / channel.platform
    subdir.mkdir(parents=True, exist_ok=True)
    with open(subdir / "repodata.json", "w") as f:
        json.dump(_export_subdir_data_to_repodata(subdir_data, index), f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    noarch = base / "noarch"
    noarch.mkdir(parents=True, exist_ok=True)
    with open(noarch / "repodata.json", "w") as f:
        json.dump({}, f)
        f.flush()
        os.fsync(f.fileno())


def _alias_canonical_channel_name_cache_to_file_prefixed(name, subdir_data=None):
    """
    This function is only temporary and meant to patch wrong / undesirable
    testing behaviour. It should end up being replaced with the new class-based,
    backend-agnostic solver tests.
    """
    # export repodata state to disk for other solvers to test
    if subdir_data is None:
        cache_key = Channel(name).url(with_credentials=True), "repodata.json"
        subdir_data = SubdirData._cache_.get(cache_key)
    if subdir_data:
        local_proxy_channel = Channel(f"{EXPORTED_CHANNELS_DIR}/{name}")
        SubdirData._cache_[
            (local_proxy_channel.url(with_credentials=True), "repodata.json")
        ] = subdir_data


def _patch_for_local_exports(name, subdir_data, channel, index):
    """
    This function is only temporary and meant to patch wrong / undesirable
    testing behaviour. It should end up being replaced with the new class-based,
    backend-agnostic solver tests.
    """
    _alias_canonical_channel_name_cache_to_file_prefixed(name, subdir_data)

    # we need to override the modification time here so the
    # cache hits this subdir_data object from the local copy too
    # - without this, the legacy solver will use the local dump too
    # and there's no need for that extra work
    # (check conda.core.subdir_data.SubdirDataType.__call__ for
    # details)
    _sync_channel_to_disk(channel, subdir_data, index)
    subdir_data._mtime = float("inf")


# this fixture appears to introduce a test-order dependency if cached
def get_index_r_1(subdir=context.subdir):
    with open(join(TEST_DATA_DIR, "index.json")) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel("https://conda.anaconda.org/channel-1/%s" % subdir)
    sd = SubdirData(channel)
    with env_var(
        "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
        "false",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd.iter_records()}
    add_feature_records_legacy(index)
    r = Resolve(index, channels=(channel,))

    _patch_for_local_exports("channel-1", sd, channel, index)
    return index, r


@lru_cache(maxsize=None)
def get_index_r_2(subdir=context.subdir):
    with open(join(TEST_DATA_DIR, "index2.json")) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel("https://conda.anaconda.org/channel-2/%s" % subdir)
    sd = SubdirData(channel)
    with env_var(
        "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
        "false",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd.iter_records()}
    r = Resolve(index, channels=(channel,))

    _patch_for_local_exports("channel-2", sd, channel, index)
    return index, r


@lru_cache(maxsize=None)
def get_index_r_4(subdir=context.subdir):
    with open(join(TEST_DATA_DIR, "index4.json")) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel("https://conda.anaconda.org/channel-4/%s" % subdir)
    sd = SubdirData(channel)
    with env_var(
        "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
        "false",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd.iter_records()}
    r = Resolve(index, channels=(channel,))

    _patch_for_local_exports("channel-4", sd, channel, index)
    return index, r


@lru_cache(maxsize=None)
def get_index_r_5(subdir=context.subdir):
    with open(join(TEST_DATA_DIR, "index5.json")) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel("https://conda.anaconda.org/channel-5/%s" % subdir)
    sd = SubdirData(channel)
    with env_var(
        "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
        "true",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd.iter_records()}
    r = Resolve(index, channels=(channel,))

    _patch_for_local_exports("channel-5", sd, channel, index)
    return index, r


@lru_cache(maxsize=None)
def get_index_must_unfreeze(subdir=context.subdir):
    repodata = {
        "info": {
            "subdir": subdir,
            "arch": context.arch_name,
            "platform": context.platform,
        },
        "packages": {
            "foobar-1.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": ["libbar 2.0.*", "libfoo 1.0.*"],
                "md5": "11ec1194bcc56b9a53c127142a272772",
                "name": "foobar",
                "timestamp": 1562861325613,
                "version": "1.0",
            },
            "foobar-2.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": ["libbar 2.0.*", "libfoo 2.0.*"],
                "md5": "f8eb5a7fa1ff6dead4e360631a6cd048",
                "name": "foobar",
                "version": "2.0",
            },
            "libbar-1.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [],
                "md5": "f51f4d48a541b7105b5e343704114f0f",
                "name": "libbar",
                "timestamp": 1562858881022,
                "version": "1.0",
            },
            "libbar-2.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [],
                "md5": "27f4e717ed263f909074f64d9cbf935d",
                "name": "libbar",
                "timestamp": 1562858881748,
                "version": "2.0",
            },
            "libfoo-1.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [],
                "md5": "ad7c088566ffe2389958daedf8ff312c",
                "name": "libfoo",
                "timestamp": 1562858763881,
                "version": "1.0",
            },
            "libfoo-2.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": [],
                "md5": "daf7af7086d8f22be49ae11bdc41f332",
                "name": "libfoo",
                "timestamp": 1562858836924,
                "version": "2.0",
            },
            "qux-1.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": ["libbar 2.0.*", "libfoo 1.0.*"],
                "md5": "18604cbe4f789fe853232eef4babd4f9",
                "name": "qux",
                "timestamp": 1562861393808,
                "version": "1.0",
            },
            "qux-2.0-0.tar.bz2": {
                "build": "0",
                "build_number": 0,
                "depends": ["libbar 1.0.*", "libfoo 2.0.*"],
                "md5": "892aa4b9ec64b67045a46866ef1ea488",
                "name": "qux",
                "timestamp": 1562861394828,
                "version": "2.0",
            },
        },
    }
    channel = Channel("https://conda.anaconda.org/channel-freeze/%s" % subdir)
    sd = SubdirData(channel)
    with env_var(
        "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
        "false",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd.iter_records()}
    r = Resolve(index, channels=(channel,))

    _patch_for_local_exports("channel-freeze", sd, channel, index)
    return index, r


# Do not memoize this get_index to allow different CUDA versions to be detected
def get_index_cuda(subdir=context.subdir):
    with open(join(TEST_DATA_DIR, "index.json")) as fi:
        packages = json.load(fi)
        repodata = {
            "info": {
                "subdir": subdir,
                "arch": context.arch_name,
                "platform": context.platform,
            },
            "packages": packages,
        }

    channel = Channel("https://conda.anaconda.org/channel-1/%s" % subdir)
    sd = SubdirData(channel)
    with env_var("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "false", reset_context):
        sd._process_raw_repodata_str(json.dumps(repodata))
    sd._loaded = True
    SubdirData._cache_[channel.url(with_credentials=True)] = sd

    index = {prec: prec for prec in sd.iter_records()}

    add_feature_records_legacy(index)
    r = Resolve(index, channels=(channel,))

    _patch_for_local_exports("channel-1", sd, channel, index)
    return index, r


def record(
    name="a",
    version="1.0",
    depends=None,
    build="0",
    build_number=0,
    timestamp=0,
    channel=None,
    **kwargs,
):
    return PackageRecord(
        name=name,
        version=version,
        depends=depends or [],
        build=build,
        build_number=build_number,
        timestamp=timestamp,
        channel=channel,
        **kwargs,
    )


@contextmanager
def get_solver(
    tmpdir, specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()
):
    tmpdir = tmpdir.strpath
    pd = PrefixData(tmpdir)
    pd._PrefixData__prefix_records = {
        rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records
    }
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_1(context.subdir)
    _alias_canonical_channel_name_cache_to_file_prefixed("channel-1")
    with patch.object(History, "get_requested_specs_map", return_value=spec_map):
        with env_var(
            "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
            "false",
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            # We need CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY=false here again (it's also in
            # get_index_r_*) to cover solver logics that need to load from disk instead of
            # hitting the SubdirData cache
            solver = context.plugin_manager.get_cached_solver_backend()(
                tmpdir,
                (Channel(f"{EXPORTED_CHANNELS_DIR}/channel-1"),),
                (context.subdir,),
                specs_to_add=specs_to_add,
                specs_to_remove=specs_to_remove,
            )
            yield solver


@contextmanager
def get_solver_2(
    tmpdir, specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()
):
    tmpdir = tmpdir.strpath
    pd = PrefixData(tmpdir)
    pd._PrefixData__prefix_records = {
        rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records
    }
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_2(context.subdir)
    _alias_canonical_channel_name_cache_to_file_prefixed("channel-2")
    with patch.object(History, "get_requested_specs_map", return_value=spec_map):
        with env_var(
            "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
            "false",
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            # We need CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY=false here again (it's also in
            # get_index_r_*) to cover solver logics that need to load from disk instead of
            # hitting the SubdirData cache
            solver = context.plugin_manager.get_cached_solver_backend()(
                tmpdir,
                (Channel(f"{EXPORTED_CHANNELS_DIR}/channel-2"),),
                (context.subdir,),
                specs_to_add=specs_to_add,
                specs_to_remove=specs_to_remove,
            )
            yield solver


@contextmanager
def get_solver_4(
    tmpdir, specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()
):
    tmpdir = tmpdir.strpath
    pd = PrefixData(tmpdir)
    pd._PrefixData__prefix_records = {
        rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records
    }
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_4(context.subdir)
    _alias_canonical_channel_name_cache_to_file_prefixed("channel-4")
    with patch.object(History, "get_requested_specs_map", return_value=spec_map):
        with env_var(
            "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
            "false",
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            # We need CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY=false here again (it's also in
            # get_index_r_*) to cover solver logics that need to load from disk instead of
            # hitting the SubdirData cache
            solver = context.plugin_manager.get_cached_solver_backend()(
                tmpdir,
                (Channel(f"{EXPORTED_CHANNELS_DIR}/channel-4"),),
                (context.subdir,),
                specs_to_add=specs_to_add,
                specs_to_remove=specs_to_remove,
            )
            yield solver


@contextmanager
def get_solver_5(
    tmpdir, specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()
):
    tmpdir = tmpdir.strpath
    pd = PrefixData(tmpdir)
    pd._PrefixData__prefix_records = {
        rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records
    }
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_5(context.subdir)
    _alias_canonical_channel_name_cache_to_file_prefixed("channel-5")
    with patch.object(History, "get_requested_specs_map", return_value=spec_map):
        with env_var(
            "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
            "false",
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            # We need CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY=false here again (it's also in
            # get_index_r_*) to cover solver logics that need to load from disk instead of
            # hitting the SubdirData cache
            solver = context.plugin_manager.get_cached_solver_backend()(
                tmpdir,
                (Channel(f"{EXPORTED_CHANNELS_DIR}/channel-5"),),
                (context.subdir,),
                specs_to_add=specs_to_add,
                specs_to_remove=specs_to_remove,
            )
            yield solver


@contextmanager
def get_solver_aggregate_1(
    tmpdir, specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()
):
    tmpdir = tmpdir.strpath
    pd = PrefixData(tmpdir)
    pd._PrefixData__prefix_records = {
        rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records
    }
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_2(context.subdir)
    get_index_r_4(context.subdir)
    _alias_canonical_channel_name_cache_to_file_prefixed("channel-2")
    _alias_canonical_channel_name_cache_to_file_prefixed("channel-4")
    with patch.object(History, "get_requested_specs_map", return_value=spec_map):
        with env_var(
            "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
            "false",
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            # We need CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY=false here again (it's also in
            # get_index_r_*) to cover solver logics that need to load from disk instead of
            # hitting the SubdirData cache
            solver = context.plugin_manager.get_cached_solver_backend()(
                tmpdir,
                (
                    Channel(f"{EXPORTED_CHANNELS_DIR}/channel-2"),
                    Channel(f"{EXPORTED_CHANNELS_DIR}/channel-4"),
                ),
                (context.subdir,),
                specs_to_add=specs_to_add,
                specs_to_remove=specs_to_remove,
            )
            yield solver


@contextmanager
def get_solver_aggregate_2(
    tmpdir, specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()
):
    tmpdir = tmpdir.strpath
    pd = PrefixData(tmpdir)
    pd._PrefixData__prefix_records = {
        rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records
    }
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_r_2(context.subdir)
    get_index_r_4(context.subdir)
    _alias_canonical_channel_name_cache_to_file_prefixed("channel-4")
    _alias_canonical_channel_name_cache_to_file_prefixed("channel-2")
    with patch.object(History, "get_requested_specs_map", return_value=spec_map):
        with env_var(
            "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
            "false",
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            # We need CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY=false here again (it's also in
            # get_index_r_*) to cover solver logics that need to load from disk instead of
            # hitting the SubdirData cache
            solver = context.plugin_manager.get_cached_solver_backend()(
                tmpdir,
                (
                    Channel(f"{EXPORTED_CHANNELS_DIR}/channel-4"),
                    Channel(f"{EXPORTED_CHANNELS_DIR}/channel-2"),
                ),
                (context.subdir,),
                specs_to_add=specs_to_add,
                specs_to_remove=specs_to_remove,
            )
            yield solver


@contextmanager
def get_solver_must_unfreeze(
    tmpdir, specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()
):
    tmpdir = tmpdir.strpath
    pd = PrefixData(tmpdir)
    pd._PrefixData__prefix_records = {
        rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records
    }
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_must_unfreeze(context.subdir)
    _alias_canonical_channel_name_cache_to_file_prefixed("channel-freeze")
    with patch.object(History, "get_requested_specs_map", return_value=spec_map):
        with env_var(
            "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
            "false",
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            # We need CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY=false here again (it's also in
            # get_index_r_*) to cover solver logics that need to load from disk instead of
            # hitting the SubdirData cache
            solver = context.plugin_manager.get_cached_solver_backend()(
                tmpdir,
                (Channel(f"{EXPORTED_CHANNELS_DIR}/channel-freeze"),),
                (context.subdir,),
                specs_to_add=specs_to_add,
                specs_to_remove=specs_to_remove,
            )
            yield solver


@contextmanager
def get_solver_cuda(
    tmpdir, specs_to_add=(), specs_to_remove=(), prefix_records=(), history_specs=()
):
    tmpdir = tmpdir.strpath
    pd = PrefixData(tmpdir)
    pd._PrefixData__prefix_records = {
        rec.name: PrefixRecord.from_objects(rec) for rec in prefix_records
    }
    spec_map = {spec.name: spec for spec in history_specs}
    get_index_cuda(context.subdir)
    _alias_canonical_channel_name_cache_to_file_prefixed("channel-1")
    with patch.object(History, "get_requested_specs_map", return_value=spec_map):
        with env_var(
            "CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY",
            "false",
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            # We need CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY=false here again (it's also in
            # get_index_r_*) to cover solver logics that need to load from disk instead of
            # hitting the SubdirData cache
            solver = context.plugin_manager.get_cached_solver_backend()(
                tmpdir,
                (Channel(f"{EXPORTED_CHANNELS_DIR}/channel-1"),),
                (context.subdir,),
                specs_to_add=specs_to_add,
                specs_to_remove=specs_to_remove,
            )
            yield solver


def convert_to_dist_str(solution):
    dist_str = []
    for prec in solution:
        # This is needed to remove the local path prefix in the
        # dist_str() calls, otherwise we cannot compare them
        canonical_name = prec.channel._Channel__canonical_name
        prec.channel._Channel__canonical_name = prec.channel.name
        dist_str.append(prec.dist_str())
        prec.channel._Channel__canonical_name = canonical_name
    return tuple(dist_str)


@pytest.fixture()
def solver_class():
    return context.plugin_manager.get_cached_solver_backend()
