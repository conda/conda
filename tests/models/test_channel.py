# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from logging import getLogger
from tempfile import gettempdir

import pytest
from pytest import MonkeyPatch

from conda.auxlib.ish import dals
from conda.base.constants import DEFAULT_CHANNELS
from conda.base.context import (
    Context,
    conda_tests_ctxt_mgmt_def_pol,
    context,
    reset_context,
)
from conda.common.configuration import YamlRawParameter
from conda.common.io import env_unmodified, env_var, env_vars
from conda.common.serialize import yaml_round_trip_load
from conda.common.url import join, join_url
from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.gateways.logging import initialize_logging
from conda.models.channel import Channel, prioritize_channels
from conda.utils import on_win

initialize_logging()
log = getLogger(__name__)


def test_channel_alias_channels():
    channel = Channel("binstar/label/dev")
    assert channel.channel_name == "binstar/label/dev"
    assert channel.channel_location == "conda.anaconda.org"
    assert channel.platform is None
    assert channel.package_filename is None
    assert channel.canonical_name == "binstar/label/dev"
    assert channel.urls() == [
        "https://conda.anaconda.org/binstar/label/dev/%s" % context.subdir,
        "https://conda.anaconda.org/binstar/label/dev/noarch",
    ]

    channel = Channel("binstar/label/dev/win-32")
    assert channel.channel_name == "binstar/label/dev"
    assert channel.channel_location == "conda.anaconda.org"
    assert channel.platform == "win-32"
    assert channel.package_filename is None
    assert channel.canonical_name == "binstar/label/dev"
    assert channel.urls() == [
        "https://conda.anaconda.org/binstar/label/dev/win-32",
        "https://conda.anaconda.org/binstar/label/dev/noarch",
    ]


def test_channel_host_port():
    channel = Channel("https://192.168.0.0:8000")
    assert channel.channel_name == ""
    assert channel.channel_location == "192.168.0.0:8000"
    assert channel.platform is None
    assert channel.package_filename is None
    assert channel.canonical_name == "https://192.168.0.0:8000"
    assert channel.urls() == [
        "https://192.168.0.0:8000/%s" % context.subdir,
        "https://192.168.0.0:8000/noarch",
    ]


def test_channel_cache():
    Channel._reset_state()
    assert len(Channel._cache_) == 0
    dc = Channel("defaults")
    assert len(Channel._cache_) == 1
    dc1 = Channel("defaults")
    assert len(Channel._cache_) == 1
    dc2 = Channel("defaults")
    assert len(Channel._cache_) == 1

    assert dc1 is dc
    assert dc2 is dc

    dc3 = Channel(dc)
    assert len(Channel._cache_) == 1
    assert dc3 is dc

    ccc = Channel("conda-canary")
    assert len(Channel._cache_) == 2

    ccc1 = Channel("conda-canary")
    assert len(Channel._cache_) == 2
    assert ccc1 is ccc


def test_default_channel():
    with env_unmodified(conda_tests_ctxt_mgmt_def_pol):
        dc = Channel("defaults")
        assert dc.canonical_name == "defaults"
        assert dc.urls() == [
            f"https://repo.anaconda.com/pkgs/main/{context.subdir}",
            "https://repo.anaconda.com/pkgs/main/noarch",
            f"https://repo.anaconda.com/pkgs/r/{context.subdir}",
            "https://repo.anaconda.com/pkgs/r/noarch",
            *(
                [
                    f"https://repo.anaconda.com/pkgs/msys2/{context.subdir}",
                    "https://repo.anaconda.com/pkgs/msys2/noarch",
                ]
                if on_win
                else []
            ),
        ]
        assert dc.subdir is None
        assert str(dc) == "defaults"

        dc = Channel("defaults/win-32")
        assert dc.canonical_name == "defaults"
        assert dc.subdir == "win-32"
        assert dc.urls()[0] == "https://repo.anaconda.com/pkgs/main/win-32"
        assert dc.urls()[1] == "https://repo.anaconda.com/pkgs/main/noarch"
        assert dc.urls()[2].endswith("/win-32")


def test_url_channel_w_platform():
    with env_unmodified(conda_tests_ctxt_mgmt_def_pol):
        channel = Channel("https://repo.anaconda.com/pkgs/main/osx-64")

        assert channel.scheme == "https"
        assert channel.location == "repo.anaconda.com"
        assert channel.platform == "osx-64" == channel.subdir
        assert channel.name == "pkgs/main"

        assert channel.base_url == "https://repo.anaconda.com/pkgs/main"
        assert channel.canonical_name == "defaults"
        assert channel.url() == "https://repo.anaconda.com/pkgs/main/osx-64"
        assert channel.urls() == [
            "https://repo.anaconda.com/pkgs/main/osx-64",
            "https://repo.anaconda.com/pkgs/main/noarch",
        ]


def test_bare_channel_http():
    url = "http://conda-01"
    channel = Channel(url)
    assert channel.scheme == "http"
    assert channel.location == "conda-01"
    assert channel.platform is None
    assert channel.canonical_name == url
    assert channel.name == ""

    assert channel.base_url == url
    assert channel.url() == join_url(url, context.subdir)
    assert channel.urls() == [
        join_url(url, context.subdir),
        join_url(url, "noarch"),
    ]


def test_bare_channel_file():
    url = "file:///conda-01"
    channel = Channel(url)
    assert channel.scheme == "file"
    assert channel.location == "/"
    assert channel.platform is None
    assert channel.canonical_name == url
    assert channel.name == "conda-01"

    assert channel.base_url == url
    assert channel.url() == join_url(url, context.subdir)
    assert channel.urls() == [
        join_url(url, context.subdir),
        join_url(url, "noarch"),
    ]


def test_channel_name_subdir_only():
    with env_unmodified(conda_tests_ctxt_mgmt_def_pol):
        channel = Channel("pkgs/main/win-64")
        assert channel.scheme == "https"
        assert channel.location == "repo.anaconda.com"
        assert channel.platform == "win-64" == channel.subdir
        assert channel.name == "pkgs/main"

        assert channel.base_url == "https://repo.anaconda.com/pkgs/main"
        assert channel.canonical_name == "defaults"
        assert channel.url() == "https://repo.anaconda.com/pkgs/main/win-64"
        assert channel.urls() == [
            "https://repo.anaconda.com/pkgs/main/win-64",
            "https://repo.anaconda.com/pkgs/main/noarch",
        ]


def test_channel_alias_w_conda_path(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("CONDA_CHANNEL_ALIAS", "https://10.2.3.4:8080/conda/t/tk-123-45")
    monkeypatch.setenv(
        "CONDA_MIGRATED_CHANNEL_ALIASES",
        "https://conda.anaconda.org,http://10.2.3.4:7070/conda",
    )
    reset_context()

    channel = Channel("bioconda")
    assert channel.channel_name == "bioconda"
    assert channel.channel_location == "10.2.3.4:8080/conda"
    assert channel.platform is None
    assert channel.package_filename is None
    assert channel.auth is None
    assert channel.scheme == "https"
    assert channel.canonical_name == "bioconda"
    assert channel.urls() == [
        f"https://10.2.3.4:8080/conda/bioconda/{context.subdir}",
        "https://10.2.3.4:8080/conda/bioconda/noarch",
    ]
    assert channel.token == "tk-123-45"
    assert str(channel) == "https://10.2.3.4:8080/conda/bioconda"
    assert (
        str(Channel("bioconda/linux-32"))
        == "https://10.2.3.4:8080/conda/bioconda/linux-32"
    )


def test_channel_alias_w_subhcnnale(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("CONDA_CHANNEL_ALIAS", "https://10.2.3.4:8080/conda/t/tk-123-45")
    monkeypatch.setenv(
        "CONDA_MIGRATED_CHANNEL_ALIASES",
        "https://conda.anaconda.org,http://10.2.3.4:7070/conda",
    )
    reset_context()

    channel = Channel("bioconda/label/dev")
    assert channel.channel_name == "bioconda/label/dev"
    assert channel.channel_location == "10.2.3.4:8080/conda"
    assert channel.platform is None
    assert channel.package_filename is None
    assert channel.auth is None
    assert channel.scheme == "https"
    assert channel.canonical_name == "bioconda/label/dev"
    assert channel.urls() == [
        f"https://10.2.3.4:8080/conda/bioconda/label/dev/{context.subdir}",
        "https://10.2.3.4:8080/conda/bioconda/label/dev/noarch",
    ]
    assert channel.token == "tk-123-45"


def test_custom_token_in_channel(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("CONDA_CHANNEL_ALIAS", "https://10.2.3.4:8080/conda/t/tk-123-45")
    monkeypatch.setenv(
        "CONDA_MIGRATED_CHANNEL_ALIASES",
        "https://conda.anaconda.org,http://10.2.3.4:7070/conda",
    )
    reset_context()

    channel = Channel("https://10.2.3.4:8080/conda/t/x1029384756/bioconda")
    assert channel.channel_name == "bioconda"
    assert channel.channel_location == "10.2.3.4:8080/conda"
    assert channel.platform is None
    assert channel.package_filename is None
    assert channel.auth is None
    assert channel.token == "x1029384756"
    assert channel.scheme == "https"
    assert channel.canonical_name == "bioconda"
    assert channel.urls() == [
        f"https://10.2.3.4:8080/conda/bioconda/{context.subdir}",
        "https://10.2.3.4:8080/conda/bioconda/noarch",
    ]


def test_canonicalized_url_gets_correct_token(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("CONDA_CHANNEL_ALIAS", "https://10.2.3.4:8080/conda/t/tk-123-45")
    monkeypatch.setenv(
        "CONDA_MIGRATED_CHANNEL_ALIASES",
        "https://conda.anaconda.org,http://10.2.3.4:7070/conda",
    )
    reset_context()

    channel = Channel("bioconda")
    assert channel.urls() == [
        f"https://10.2.3.4:8080/conda/bioconda/{context.subdir}",
        "https://10.2.3.4:8080/conda/bioconda/noarch",
    ]
    assert channel.urls(with_credentials=True) == [
        f"https://10.2.3.4:8080/conda/t/tk-123-45/bioconda/{context.subdir}",
        "https://10.2.3.4:8080/conda/t/tk-123-45/bioconda/noarch",
    ]

    channel = Channel("https://10.2.3.4:8080/conda/bioconda")
    assert channel.urls() == [
        f"https://10.2.3.4:8080/conda/bioconda/{context.subdir}",
        "https://10.2.3.4:8080/conda/bioconda/noarch",
    ]
    assert channel.urls(with_credentials=True) == [
        f"https://10.2.3.4:8080/conda/t/tk-123-45/bioconda/{context.subdir}",
        "https://10.2.3.4:8080/conda/t/tk-123-45/bioconda/noarch",
    ]

    channel = Channel("https://10.2.3.4:8080/conda/t/x1029384756/bioconda")
    assert channel.urls() == [
        f"https://10.2.3.4:8080/conda/bioconda/{context.subdir}",
        "https://10.2.3.4:8080/conda/bioconda/noarch",
    ]
    assert channel.urls(with_credentials=True) == [
        f"https://10.2.3.4:8080/conda/t/x1029384756/bioconda/{context.subdir}",
        "https://10.2.3.4:8080/conda/t/x1029384756/bioconda/noarch",
    ]

    # what happens with the token if it's in the wrong places?
    channel = Channel("https://10.2.3.4:8080/t/x1029384756/conda/bioconda")
    assert channel.urls() == [
        f"https://10.2.3.4:8080/conda/bioconda/{context.subdir}",
        "https://10.2.3.4:8080/conda/bioconda/noarch",
    ]
    assert channel.urls(with_credentials=True) == [
        f"https://10.2.3.4:8080/conda/t/x1029384756/bioconda/{context.subdir}",
        "https://10.2.3.4:8080/conda/t/x1029384756/bioconda/noarch",
    ]


def test_token_in_custom_channel():
    channel = Channel("https://10.2.8.9:8080/conda/t/tk-987-321/bioconda/label/dev")
    assert channel.name == "bioconda/label/dev"
    assert channel.location == "10.2.8.9:8080/conda"
    assert channel.urls() == [
        f"https://10.2.8.9:8080/conda/bioconda/label/dev/{context.subdir}",
        "https://10.2.8.9:8080/conda/bioconda/label/dev/noarch",
    ]
    assert channel.urls(with_credentials=True) == [
        f"https://10.2.8.9:8080/conda/t/tk-987-321/bioconda/label/dev/{context.subdir}",
        "https://10.2.8.9:8080/conda/t/tk-987-321/bioconda/label/dev/noarch",
    ]

    channel = Channel("https://10.2.8.9:8080/conda/t/tk-987-321/bioconda")
    assert channel.name == "bioconda"
    assert channel.location == "10.2.8.9:8080/conda"
    assert channel.urls() == [
        f"https://10.2.8.9:8080/conda/bioconda/{context.subdir}",
        "https://10.2.8.9:8080/conda/bioconda/noarch",
    ]
    assert channel.urls(with_credentials=True) == [
        f"https://10.2.8.9:8080/conda/t/tk-987-321/bioconda/{context.subdir}",
        "https://10.2.8.9:8080/conda/t/tk-987-321/bioconda/noarch",
    ]


@pytest.fixture
def testdata() -> None:
    """
    Some notes about the tests in this class:
      * The 'pkgs/anaconda' channel is 'migrated' while the 'pkgs/pro' channel is not.
        Thus test_pkgs_free and test_pkgs_pro have substantially different behavior.
    """
    reset_context()
    context._set_raw_data(
        {
            "testdata": YamlRawParameter.make_raw_parameters(
                "testdata",
                yaml_round_trip_load(
                    dals(
                        """
                        custom_channels:
                          darwin: https://some.url.somewhere/stuff
                          chuck: http://user1:pass2@another.url:8080/t/tk-1234/with/path
                          pkgs/anaconda: http://192.168.0.15:8080
                        migrated_custom_channels:
                          darwin: s3://just/cant
                          chuck: file:///var/lib/repo/
                          pkgs/anaconda: https://repo.anaconda.com
                        migrated_channel_aliases:
                          - https://conda.anaconda.org
                        channel_alias: ftp://new.url:8082
                        default_channels:
                          - http://192.168.0.15:8080/pkgs/anaconda
                          - http://192.168.0.15:8080/pkgs/pro
                          - http://192.168.0.15:8080/pkgs/msys2
                        """
                    )
                ),
            )
        }
    )
    Channel._reset_state()


def test_pkgs_main(testdata: None):
    channel = Channel("pkgs/anaconda")
    assert channel.channel_name == "pkgs/anaconda"
    assert channel.channel_location == "192.168.0.15:8080"
    assert channel.canonical_name == "defaults"
    assert channel.urls() == [
        f"http://192.168.0.15:8080/pkgs/anaconda/{context.subdir}",
        "http://192.168.0.15:8080/pkgs/anaconda/noarch",
    ]

    channel = Channel("https://repo.anaconda.com/pkgs/anaconda")
    assert channel.channel_name == "pkgs/anaconda"
    assert channel.channel_location == "192.168.0.15:8080"
    assert channel.canonical_name == "defaults"
    assert channel.urls() == [
        f"http://192.168.0.15:8080/pkgs/anaconda/{context.subdir}",
        "http://192.168.0.15:8080/pkgs/anaconda/noarch",
    ]

    channel = Channel("https://repo.anaconda.com/pkgs/anaconda/noarch")
    assert channel.channel_name == "pkgs/anaconda"
    assert channel.channel_location == "192.168.0.15:8080"
    assert channel.canonical_name == "defaults"
    assert channel.urls() == [
        "http://192.168.0.15:8080/pkgs/anaconda/noarch",
    ]

    channel = Channel("https://repo.anaconda.com/pkgs/anaconda/label/dev")
    assert channel.channel_name == "pkgs/anaconda/label/dev"
    assert channel.channel_location == "192.168.0.15:8080"
    assert channel.canonical_name == "pkgs/anaconda/label/dev"
    assert channel.urls() == [
        f"http://192.168.0.15:8080/pkgs/anaconda/label/dev/{context.subdir}",
        "http://192.168.0.15:8080/pkgs/anaconda/label/dev/noarch",
    ]

    channel = Channel(
        "https://repo.anaconda.com/pkgs/anaconda/noarch/flask-1.0.tar.bz2"
    )
    assert channel.channel_name == "pkgs/anaconda"
    assert channel.channel_location == "192.168.0.15:8080"
    assert channel.platform == "noarch"
    assert channel.package_filename == "flask-1.0.tar.bz2"
    assert channel.canonical_name == "defaults"
    assert channel.urls() == [
        "http://192.168.0.15:8080/pkgs/anaconda/noarch",
    ]
    channel = Channel("https://repo.anaconda.com/pkgs/anaconda/noarch/flask-1.0.conda")
    assert channel.channel_name == "pkgs/anaconda"
    assert channel.channel_location == "192.168.0.15:8080"
    assert channel.platform == "noarch"
    assert channel.package_filename == "flask-1.0.conda"
    assert channel.canonical_name == "defaults"
    assert channel.urls() == [
        "http://192.168.0.15:8080/pkgs/anaconda/noarch",
    ]


def test_pkgs_pro(testdata: None):
    channel = Channel("pkgs/pro")
    assert channel.channel_name == "pkgs/pro"
    assert channel.channel_location == "192.168.0.15:8080"
    assert channel.canonical_name == "defaults"
    assert channel.urls() == [
        f"http://192.168.0.15:8080/pkgs/pro/{context.subdir}",
        "http://192.168.0.15:8080/pkgs/pro/noarch",
    ]

    channel = Channel("https://repo.anaconda.com/pkgs/pro")
    assert channel.channel_name == "pkgs/pro"
    assert channel.channel_location == "repo.anaconda.com"
    assert channel.canonical_name == "defaults"
    assert channel.urls() == [
        f"https://repo.anaconda.com/pkgs/pro/{context.subdir}",
        "https://repo.anaconda.com/pkgs/pro/noarch",
    ]

    channel = Channel("https://repo.anaconda.com/pkgs/pro/noarch")
    assert channel.channel_name == "pkgs/pro"
    assert channel.channel_location == "repo.anaconda.com"
    assert channel.canonical_name == "defaults"
    assert channel.urls() == [
        "https://repo.anaconda.com/pkgs/pro/noarch",
    ]

    channel = Channel("https://repo.anaconda.com/pkgs/pro/label/dev")
    assert channel.channel_name == "pkgs/pro/label/dev"
    assert channel.channel_location == "repo.anaconda.com"
    assert channel.canonical_name == "pkgs/pro/label/dev"
    assert channel.urls() == [
        f"https://repo.anaconda.com/pkgs/pro/label/dev/{context.subdir}",
        "https://repo.anaconda.com/pkgs/pro/label/dev/noarch",
    ]

    channel = Channel("https://repo.anaconda.com/pkgs/pro/noarch/flask-1.0.tar.bz2")
    assert channel.channel_name == "pkgs/pro"
    assert channel.channel_location == "repo.anaconda.com"
    assert channel.platform == "noarch"
    assert channel.package_filename == "flask-1.0.tar.bz2"
    assert channel.canonical_name == "defaults"
    assert channel.urls() == [
        "https://repo.anaconda.com/pkgs/pro/noarch",
    ]


def test_custom_channels(testdata: None):
    channel = Channel("darwin")
    assert channel.channel_name == "darwin"
    assert channel.channel_location == "some.url.somewhere/stuff"

    channel = Channel("https://some.url.somewhere/stuff/darwin")
    assert channel.channel_name == "darwin"
    assert channel.channel_location == "some.url.somewhere/stuff"

    channel = Channel("https://some.url.somewhere/stuff/darwin/label/dev")
    assert channel.channel_name == "darwin/label/dev"
    assert channel.channel_location == "some.url.somewhere/stuff"
    assert channel.platform is None

    channel = Channel("https://some.url.somewhere/stuff/darwin/label/dev/linux-64")
    assert channel.channel_name == "darwin/label/dev"
    assert channel.channel_location == "some.url.somewhere/stuff"
    assert channel.platform == "linux-64"
    assert channel.package_filename is None

    channel = Channel(
        "https://some.url.somewhere/stuff/darwin/label/dev/linux-64/flask-1.0.tar.bz2"
    )
    assert channel.channel_name == "darwin/label/dev"
    assert channel.channel_location == "some.url.somewhere/stuff"
    assert channel.platform == "linux-64"
    assert channel.package_filename == "flask-1.0.tar.bz2"
    assert channel.auth is None
    assert channel.token is None
    assert channel.scheme == "https"

    channel = Channel(
        "https://some.url.somewhere/stuff/darwin/label/dev/linux-64/flask-1.0.tar.bz2"
    )
    assert channel.channel_name == "darwin/label/dev"
    assert channel.channel_location == "some.url.somewhere/stuff"
    assert channel.platform == "linux-64"
    assert channel.package_filename == "flask-1.0.tar.bz2"
    assert channel.auth is None
    assert channel.token is None
    assert channel.scheme == "https"


def test_custom_channels_port_token_auth(testdata: None):
    channel = Channel("chuck")
    assert channel.channel_name == "chuck"
    assert channel.channel_location == "another.url:8080/with/path"
    assert channel.auth == "user1:pass2"
    assert channel.token == "tk-1234"
    assert channel.scheme == "http"

    channel = Channel(
        "https://another.url:8080/with/path/chuck/label/dev/linux-64/flask-1.0.tar.bz2"
    )
    assert channel.channel_name == "chuck/label/dev"
    assert channel.channel_location == "another.url:8080/with/path"
    assert channel.auth == "user1:pass2"
    assert channel.token == "tk-1234"
    assert channel.scheme == "https"
    assert channel.platform == "linux-64"
    assert channel.package_filename == "flask-1.0.tar.bz2"


def test_migrated_custom_channels(testdata: None):
    channel = Channel("s3://just/cant/darwin/osx-64")
    assert channel.channel_name == "darwin"
    assert channel.channel_location == "some.url.somewhere/stuff"
    assert channel.platform == "osx-64"
    assert channel.package_filename is None
    assert channel.auth is None
    assert channel.token is None
    assert channel.scheme == "https"
    assert channel.canonical_name == "darwin"
    assert channel.url() == "https://some.url.somewhere/stuff/darwin/osx-64"
    assert channel.urls() == [
        "https://some.url.somewhere/stuff/darwin/osx-64",
        "https://some.url.somewhere/stuff/darwin/noarch",
    ]
    assert Channel(channel.canonical_name).urls() == [
        f"https://some.url.somewhere/stuff/darwin/{context.subdir}",
        "https://some.url.somewhere/stuff/darwin/noarch",
    ]

    channel = Channel(
        "https://some.url.somewhere/stuff/darwin/noarch/a-mighty-fine.tar.bz2"
    )
    assert channel.channel_name == "darwin"
    assert channel.channel_location == "some.url.somewhere/stuff"
    assert channel.platform == "noarch"
    assert channel.package_filename == "a-mighty-fine.tar.bz2"
    assert channel.auth is None
    assert channel.token is None
    assert channel.scheme == "https"
    assert channel.canonical_name == "darwin"
    assert (
        channel.url()
        == "https://some.url.somewhere/stuff/darwin/noarch/a-mighty-fine.tar.bz2"
    )
    assert channel.urls() == [
        "https://some.url.somewhere/stuff/darwin/noarch",
    ]
    assert Channel(channel.canonical_name).urls() == [
        f"https://some.url.somewhere/stuff/darwin/{context.subdir}",
        "https://some.url.somewhere/stuff/darwin/noarch",
    ]


def test_local_channel(testdata: None):
    conda_bld_path = join(gettempdir(), "conda-bld")
    mkdir_p(conda_bld_path)
    try:
        with env_var(
            "CONDA_CROOT",
            conda_bld_path,
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            Channel._reset_state()
            channel = Channel("local")
            assert channel._channels[0].name.rsplit("/", 1)[-1] == "conda-bld"
            assert channel.channel_name == "local"
            assert channel.platform is None
            assert channel.package_filename is None
            assert channel.auth is None
            assert channel.token is None
            assert channel.scheme is None
            assert channel.canonical_name == "local"
            local_channel_first_subchannel = channel._channels[0].name

            channel = Channel(local_channel_first_subchannel)
            assert channel.channel_name == local_channel_first_subchannel
            assert channel.platform is None
            assert channel.package_filename is None
            assert channel.auth is None
            assert channel.token is None
            assert channel.scheme == "file"
            assert channel.canonical_name == "local"

            assert channel.urls() == Channel(local_channel_first_subchannel).urls()
            assert channel.urls()[0].startswith("file:///")
    finally:
        rm_rf(conda_bld_path)


def test_defaults_channel(testdata: None):
    channel = Channel("defaults")
    assert channel.name == "defaults"
    assert channel.platform is None
    assert channel.package_filename is None
    assert channel.auth is None
    assert channel.token is None
    assert channel.scheme is None
    assert channel.canonical_name == "defaults"
    assert channel.urls() == [
        f"http://192.168.0.15:8080/pkgs/anaconda/{context.subdir}",
        "http://192.168.0.15:8080/pkgs/anaconda/noarch",
        f"http://192.168.0.15:8080/pkgs/pro/{context.subdir}",
        "http://192.168.0.15:8080/pkgs/pro/noarch",
        f"http://192.168.0.15:8080/pkgs/msys2/{context.subdir}",
        "http://192.168.0.15:8080/pkgs/msys2/noarch",
    ]


def test_file_channel(testdata: None):
    channel = Channel(
        "file:///var/folders/cp/7r2s_s593j7_cpdtp/T/5d9f5e45/osx-64/flask-0.10.1-py35_2.tar.bz2"
    )
    assert channel.name == "5d9f5e45"
    assert channel.location == "/var/folders/cp/7r2s_s593j7_cpdtp/T"
    assert channel.platform == "osx-64"
    assert channel.package_filename == "flask-0.10.1-py35_2.tar.bz2"
    assert channel.auth is None
    assert channel.token is None
    assert channel.scheme == "file"
    assert (
        channel.url()
        == "file:///var/folders/cp/7r2s_s593j7_cpdtp/T/5d9f5e45/osx-64/flask-0.10.1-py35_2.tar.bz2"
    )
    assert channel.urls() == [
        "file:///var/folders/cp/7r2s_s593j7_cpdtp/T/5d9f5e45/osx-64",
        "file:///var/folders/cp/7r2s_s593j7_cpdtp/T/5d9f5e45/noarch",
    ]
    assert (
        channel.canonical_name == "file:///var/folders/cp/7r2s_s593j7_cpdtp/T/5d9f5e45"
    )


def test_old_channel_alias(testdata: None):
    cf_urls = [
        f"ftp://new.url:8082/conda-forge/{context.subdir}",
        "ftp://new.url:8082/conda-forge/noarch",
    ]
    assert Channel("conda-forge").urls() == cf_urls

    url = "https://conda.anaconda.org/conda-forge/osx-64/some-great-package.tar.bz2"
    assert Channel(url).canonical_name == "conda-forge"
    assert Channel(url).base_url == "ftp://new.url:8082/conda-forge"
    assert (
        Channel(url).url()
        == "ftp://new.url:8082/conda-forge/osx-64/some-great-package.tar.bz2"
    )
    assert Channel(url).urls() == [
        "ftp://new.url:8082/conda-forge/osx-64",
        "ftp://new.url:8082/conda-forge/noarch",
    ]

    channel = Channel(
        "https://conda.anaconda.org/conda-forge/label/dev/linux-64/some-great-package.tar.bz2"
    )
    assert (
        channel.url()
        == "ftp://new.url:8082/conda-forge/label/dev/linux-64/some-great-package.tar.bz2"
    )
    assert channel.urls() == [
        "ftp://new.url:8082/conda-forge/label/dev/linux-64",
        "ftp://new.url:8082/conda-forge/label/dev/noarch",
    ]


@pytest.fixture
def testdata2() -> None:
    reset_context()
    context._set_raw_data(
        {
            "testdata": YamlRawParameter.make_raw_parameters(
                "testdata",
                yaml_round_trip_load(
                    dals(
                        """
                        channels:
                          - http://user22:$EXPANDED_PWD@some.url:8080

                        allowlist_channels:
                          - http://user22:$EXPANDED_PWD@some.url:8080

                        custom_channels:
                          unexpanded: http://user1:$UNEXPANDED_PWD@another.url:8080/with/path/t/tk-1234
                          expanded: http://user33:$EXPANDED_PWD@another.url:8080/with/path/t/tk-1234
                        """
                    )
                ),
            )
        }
    )
    Channel._reset_state()


def test_unexpanded_variables(testdata2: None):
    with env_var("EXPANDED_PWD", "pass44"):
        channel = Channel("unexpanded")
        assert channel.auth == "user1:$UNEXPANDED_PWD"


def test_expanded_variables(testdata2: None):
    with env_var("EXPANDED_PWD", "pass44"):
        channel = Channel("expanded")
        assert channel.auth == "user33:pass44"
        assert context.channels[0] == "http://user22:pass44@some.url:8080"
        assert context.allowlist_channels[0] == "http://user22:pass44@some.url:8080"


@pytest.fixture
def testdata3() -> None:
    reset_context()
    context._set_raw_data(
        {
            "testdata": YamlRawParameter.make_raw_parameters(
                "testdata",
                yaml_round_trip_load(
                    dals(
                        """
                        custom_channels:
                          chuck: http://user1:pass2@another.url:8080/with/path/t/tk-1234
                          chuck/subchan: http://user33:pass44@another.url:8080/with/path/t/tk-1234
                        channel_alias: ftp://nm:ps@new.url:8082/t/zyx-wvut/
                        channels:
                          - mickey
                          - https://conda.anaconda.cloud/t/tk-12-token/minnie
                          - http://dont-do:this@4.3.2.1/daffy/label/main
                        default_channels:
                          - http://192.168.0.15:8080/pkgs/anaconda
                          - donald/label/main
                          - http://us:pw@192.168.0.15:8080/t/tkn-123/pkgs/r
                        """
                    )
                ),
            )
        }
    )
    Channel._reset_state()


def test_named_custom_channel(testdata3: None):
    channel = Channel("chuck")
    assert channel.canonical_name == "chuck"
    assert channel.location == "another.url:8080/with/path"
    assert channel.url() == f"http://another.url:8080/with/path/chuck/{context.subdir}"
    assert (
        channel.url(True)
        == f"http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/{context.subdir}"
    )
    assert channel.urls() == [
        f"http://another.url:8080/with/path/chuck/{context.subdir}",
        "http://another.url:8080/with/path/chuck/noarch",
    ]
    assert channel.urls(True) == [
        f"http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/{context.subdir}",
        "http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/noarch",
    ]

    channel = Channel("chuck/label/dev")
    assert channel.canonical_name == "chuck/label/dev"
    assert channel.location == "another.url:8080/with/path"
    assert (
        channel.url()
        == f"http://another.url:8080/with/path/chuck/label/dev/{context.subdir}"
    )
    assert (
        channel.url(True)
        == f"http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/label/dev/{context.subdir}"
    )
    assert channel.urls() == [
        f"http://another.url:8080/with/path/chuck/label/dev/{context.subdir}",
        "http://another.url:8080/with/path/chuck/label/dev/noarch",
    ]
    assert channel.urls(True) == [
        f"http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/label/dev/{context.subdir}",
        "http://user1:pass2@another.url:8080/with/path/t/tk-1234/chuck/label/dev/noarch",
    ]


def test_url_custom_channel(testdata3: None):
    # scheme and credentials within url should override what's registered in config
    channel = Channel(
        "https://newuser:newpass@another.url:8080/with/path/t/new-token/chuck/label/dev"
    )
    assert channel.canonical_name == "chuck/label/dev"
    assert channel.location == "another.url:8080/with/path"
    assert (
        channel.url()
        == f"https://another.url:8080/with/path/chuck/label/dev/{context.subdir}"
    )
    assert (
        channel.url(True)
        == f"https://newuser:newpass@another.url:8080/with/path/t/new-token/chuck/label/dev/{context.subdir}"
    )
    assert channel.urls() == [
        f"https://another.url:8080/with/path/chuck/label/dev/{context.subdir}",
        "https://another.url:8080/with/path/chuck/label/dev/noarch",
    ]
    assert channel.urls(True) == [
        f"https://newuser:newpass@another.url:8080/with/path/t/new-token/chuck/label/dev/{context.subdir}",
        "https://newuser:newpass@another.url:8080/with/path/t/new-token/chuck/label/dev/noarch",
    ]


def test_named_custom_channel_w_subchan(testdata3: None):
    channel = Channel("chuck/subchan")
    assert channel.canonical_name == "chuck/subchan"
    assert channel.location == "another.url:8080/with/path"
    assert (
        channel.url()
        == f"http://another.url:8080/with/path/chuck/subchan/{context.subdir}"
    )
    assert (
        channel.url(True)
        == f"http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/{context.subdir}"
    )
    assert channel.urls() == [
        f"http://another.url:8080/with/path/chuck/subchan/{context.subdir}",
        "http://another.url:8080/with/path/chuck/subchan/noarch",
    ]
    assert channel.urls(True) == [
        f"http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/{context.subdir}",
        "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/noarch",
    ]

    channel = Channel("chuck/subchan/label/main")
    assert channel.canonical_name == "chuck/subchan/label/main"
    assert channel.location == "another.url:8080/with/path"
    assert (
        channel.url()
        == f"http://another.url:8080/with/path/chuck/subchan/label/main/{context.subdir}"
    )
    assert (
        channel.url(True)
        == f"http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/{context.subdir}"
    )
    assert channel.urls() == [
        f"http://another.url:8080/with/path/chuck/subchan/label/main/{context.subdir}",
        "http://another.url:8080/with/path/chuck/subchan/label/main/noarch",
    ]
    assert channel.urls(True) == [
        f"http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/{context.subdir}",
        "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/noarch",
    ]


def test_url_custom_channel_w_subchan(testdata3: None):
    channel = Channel("http://another.url:8080/with/path/chuck/subchan/label/main")
    assert channel.canonical_name == "chuck/subchan/label/main"
    assert channel.location == "another.url:8080/with/path"
    assert (
        channel.url()
        == f"http://another.url:8080/with/path/chuck/subchan/label/main/{context.subdir}"
    )
    assert (
        channel.url(True)
        == f"http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/{context.subdir}"
    )
    assert channel.urls() == [
        f"http://another.url:8080/with/path/chuck/subchan/label/main/{context.subdir}",
        "http://another.url:8080/with/path/chuck/subchan/label/main/noarch",
    ]
    assert channel.urls(True) == [
        f"http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/{context.subdir}",
        "http://user33:pass44@another.url:8080/with/path/t/tk-1234/chuck/subchan/label/main/noarch",
    ]


def test_channel_alias(testdata3: None):
    channel = Channel("charlie")
    assert channel.canonical_name == "charlie"
    assert channel.location == "new.url:8082"
    assert channel.url() == f"ftp://new.url:8082/charlie/{context.subdir}"
    assert (
        channel.url(True)
        == f"ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/{context.subdir}"
    )
    assert channel.urls() == [
        f"ftp://new.url:8082/charlie/{context.subdir}",
        "ftp://new.url:8082/charlie/noarch",
    ]
    assert channel.urls(True) == [
        f"ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/{context.subdir}",
        "ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/noarch",
    ]

    channel = Channel("charlie/label/dev")
    assert channel.canonical_name == "charlie/label/dev"
    assert channel.location == "new.url:8082"
    assert channel.url() == f"ftp://new.url:8082/charlie/label/dev/{context.subdir}"
    assert (
        channel.url(True)
        == f"ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/label/dev/{context.subdir}"
    )
    assert channel.urls() == [
        f"ftp://new.url:8082/charlie/label/dev/{context.subdir}",
        "ftp://new.url:8082/charlie/label/dev/noarch",
    ]
    assert channel.urls(True) == [
        f"ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/label/dev/{context.subdir}",
        "ftp://nm:ps@new.url:8082/t/zyx-wvut/charlie/label/dev/noarch",
    ]

    channel = Channel("ftp://nm:ps@new.url:8082/t/new-token/charlie/label/dev")
    assert channel.canonical_name == "charlie/label/dev"
    assert channel.location == "new.url:8082"
    assert channel.url() == f"ftp://new.url:8082/charlie/label/dev/{context.subdir}"
    assert (
        channel.url(True)
        == f"ftp://nm:ps@new.url:8082/t/new-token/charlie/label/dev/{context.subdir}"
    )
    assert channel.urls() == [
        f"ftp://new.url:8082/charlie/label/dev/{context.subdir}",
        "ftp://new.url:8082/charlie/label/dev/noarch",
    ]
    assert channel.urls(True) == [
        f"ftp://nm:ps@new.url:8082/t/new-token/charlie/label/dev/{context.subdir}",
        "ftp://nm:ps@new.url:8082/t/new-token/charlie/label/dev/noarch",
    ]


def test_default_channels(testdata3: None):
    channel = Channel("defaults")
    assert channel.canonical_name == "defaults"
    assert channel.location is None
    assert channel.url() is None
    assert channel.url(True) is None
    assert channel.urls() == [
        f"http://192.168.0.15:8080/pkgs/anaconda/{context.subdir}",
        "http://192.168.0.15:8080/pkgs/anaconda/noarch",
        f"ftp://new.url:8082/donald/label/main/{context.subdir}",
        "ftp://new.url:8082/donald/label/main/noarch",
        f"http://192.168.0.15:8080/pkgs/r/{context.subdir}",
        "http://192.168.0.15:8080/pkgs/r/noarch",
    ]
    assert channel.urls(True) == [
        f"http://192.168.0.15:8080/pkgs/anaconda/{context.subdir}",
        "http://192.168.0.15:8080/pkgs/anaconda/noarch",
        f"ftp://nm:ps@new.url:8082/t/zyx-wvut/donald/label/main/{context.subdir}",
        "ftp://nm:ps@new.url:8082/t/zyx-wvut/donald/label/main/noarch",
        f"http://us:pw@192.168.0.15:8080/t/tkn-123/pkgs/r/{context.subdir}",
        "http://us:pw@192.168.0.15:8080/t/tkn-123/pkgs/r/noarch",
    ]

    channel = Channel("ftp://new.url:8082/donald/label/main")
    assert channel.canonical_name == "defaults"

    channel = Channel("donald/label/main")
    assert channel.canonical_name == "defaults"

    channel = Channel("ftp://new.url:8081/donald")
    assert channel.location == "new.url:8081"
    assert channel.canonical_name == "donald"


def test_file_urls():
    url = "file:///machine/shared_folder"
    c = Channel(url)
    assert c.scheme == "file"
    assert c.auth is None
    assert c.location == "/machine"
    assert c.token is None
    assert c.name == "shared_folder"
    assert c.platform is None
    assert c.package_filename is None

    assert c.canonical_name == "file:///machine/shared_folder"
    assert c.url() == "file:///machine/shared_folder/%s" % context.subdir
    assert c.urls() == [
        "file:///machine/shared_folder/%s" % context.subdir,
        "file:///machine/shared_folder/noarch",
    ]


def test_file_url_with_backslashes():
    url = "file://\\machine\\shared_folder\\path\\conda"
    c = Channel(url)
    assert c.scheme == "file"
    assert c.auth is None
    assert c.location == "/machine/shared_folder/path"
    assert c.token is None
    assert c.name == "conda"
    assert c.platform is None
    assert c.package_filename is None

    assert c.canonical_name == "file:///machine/shared_folder/path/conda"
    assert c.url() == "file:///machine/shared_folder/path/conda/%s" % context.subdir
    assert c.urls() == [
        "file:///machine/shared_folder/path/conda/%s" % context.subdir,
        "file:///machine/shared_folder/path/conda/noarch",
    ]


def test_env_var_file_urls():
    channels = (
        "file://\\\\network_share\\shared_folder\\path\\conda",
        "https://some.url/ch_name",
        "file:///some/place/on/my/machine",
    )
    with env_var("CONDA_CHANNELS", ",".join(channels)):
        new_context = Context(())
        assert new_context.channels == channels

        prioritized = prioritize_channels(new_context.channels)
        network_share = "file://network_share/shared_folder/path/conda"
        some_url = "https://some.url/ch_name"
        local_path = "file:///some/place/on/my/machine"
        assert prioritized == {
            f"{network_share}/{context.subdir}": (network_share, 0),
            f"{network_share}/noarch": (network_share, 0),
            f"{some_url}/{context.subdir}": (some_url, 1),
            f"{some_url}/noarch": (some_url, 1),
            f"{local_path}/{context.subdir}": (local_path, 2),
            f"{local_path}/noarch": (local_path, 2),
        }


def test_subdirs_env_var():
    subdirs = ("linux-highest", "linux-64", "noarch")

    def _channel_urls(channels=None):
        for channel in channels or DEFAULT_CHANNELS:
            channel = Channel(channel)
            for subdir in subdirs:
                yield join_url(channel.base_url, subdir)

    with env_vars(
        {"CONDA_SUBDIRS": ",".join(subdirs)},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        c = Channel("defaults")
        assert c.urls() == list(_channel_urls())

        c = Channel("conda-forge")
        assert c.urls() == list(_channel_urls(("conda-forge",)))

        channels = ("bioconda", "conda-forge")
        prioritized = prioritize_channels(channels)
        assert prioritized == {
            "https://conda.anaconda.org/bioconda/linux-highest": ("bioconda", 0),
            "https://conda.anaconda.org/bioconda/linux-64": ("bioconda", 0),
            "https://conda.anaconda.org/bioconda/noarch": ("bioconda", 0),
            "https://conda.anaconda.org/conda-forge/linux-highest": (
                "conda-forge",
                1,
            ),
            "https://conda.anaconda.org/conda-forge/linux-64": ("conda-forge", 1),
            "https://conda.anaconda.org/conda-forge/noarch": ("conda-forge", 1),
        }

        prioritized = prioritize_channels(channels, subdirs=("linux-again", "noarch"))
        assert prioritized == {
            "https://conda.anaconda.org/bioconda/linux-again": ("bioconda", 0),
            "https://conda.anaconda.org/bioconda/noarch": ("bioconda", 0),
            "https://conda.anaconda.org/conda-forge/linux-again": (
                "conda-forge",
                1,
            ),
            "https://conda.anaconda.org/conda-forge/noarch": ("conda-forge", 1),
        }


def test_subdir_env_var():
    with env_var(
        "CONDA_SUBDIR",
        "osx-1012-x84_64",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        channel = Channel(
            "https://conda.anaconda.org/msarahan/osx-1012-x84_64/clangxx_osx-1012-x86_64-10.12-h0bb54af_0.tar.bz2"
        )
        assert channel.base_url == "https://conda.anaconda.org/msarahan"
        assert (
            channel.package_filename
            == "clangxx_osx-1012-x86_64-10.12-h0bb54af_0.tar.bz2"
        )
        assert (
            channel.platform == "osx-1012-x84_64"
        )  # the platform attribute is misnamed here in conda 4.3; conda 4.4 code can correctly use the channel.subdir attribute


def test_regression_against_unknown_none():
    defaults = Channel("defaults")

    channel = Channel(None)
    assert channel.scheme is None
    assert channel.location is None
    assert channel.platform is None
    assert channel.name == "<unknown>"
    assert channel.canonical_name == "<unknown>"

    assert channel.base_url is None
    assert channel.url() == defaults.url()
    assert channel.urls() == defaults.urls()

    channel = Channel("<unknown>")
    assert channel.scheme is None
    assert channel.location is None
    assert channel.platform is None
    assert channel.name == "<unknown>"
    assert channel.canonical_name == "<unknown>"

    assert channel.base_url is None
    assert channel.url() == defaults.url()
    assert channel.urls() == defaults.urls()

    channel = Channel("None:///<unknown>")
    assert channel.scheme is None
    assert channel.location is None
    assert channel.platform is None
    assert channel.name == "<unknown>"
    assert channel.canonical_name == "<unknown>"

    assert channel.base_url is None
    assert channel.url() == defaults.url()
    assert channel.urls() == defaults.urls()

    channel = Channel("None")
    assert channel.scheme is None
    assert channel.location is None
    assert channel.platform is None
    assert channel.name == "<unknown>"
    assert channel.canonical_name == "<unknown>"

    assert channel.base_url is None
    assert channel.url() == defaults.url()
    assert channel.urls() == defaults.urls()


@pytest.fixture
def testdata4() -> None:
    reset_context()
    context._set_raw_data(
        {
            "testdata": YamlRawParameter.make_raw_parameters(
                "testdata",
                yaml_round_trip_load(
                    dals(
                        """
                        default_channels:
                           - http://test/conda/anaconda
                        channels:
                           - http://test/conda/anaconda-cluster
                        """
                    )
                ),
            )
        }
    )
    Channel._reset_state()


def test_channels_with_dashes(testdata4: None):
    # regression test for #5763
    assert context.channels[0] == "http://test/conda/anaconda-cluster"
    channel_urls = prioritize_channels(context.channels)
    channel_urls = tuple(channel_urls.items())
    assert channel_urls[0] == (
        "http://test/conda/anaconda-cluster/%s" % context.subdir,
        ("http://test/conda/anaconda-cluster", 0),
    )
    assert channel_urls[1] == (
        "http://test/conda/anaconda-cluster/noarch",
        ("http://test/conda/anaconda-cluster", 0),
    )


def test_multichannel_priority():
    with env_unmodified(conda_tests_ctxt_mgmt_def_pol):
        channels = ["conda-test", "defaults", "conda-forge"]
        subdirs = ["new-optimized-subdir", "linux-32", "noarch"]
        channel_priority_map = prioritize_channels(
            channels, with_credentials=True, subdirs=subdirs
        )
        if on_win:
            assert channel_priority_map == {
                "https://conda.anaconda.org/conda-test/new-optimized-subdir": (
                    "conda-test",
                    0,
                ),
                "https://conda.anaconda.org/conda-test/linux-32": ("conda-test", 0),
                "https://conda.anaconda.org/conda-test/noarch": ("conda-test", 0),
                "https://repo.anaconda.com/pkgs/main/new-optimized-subdir": (
                    "defaults",
                    1,
                ),
                "https://repo.anaconda.com/pkgs/main/linux-32": ("defaults", 1),
                "https://repo.anaconda.com/pkgs/main/noarch": ("defaults", 1),
                "https://repo.anaconda.com/pkgs/r/new-optimized-subdir": (
                    "defaults",
                    2,
                ),
                "https://repo.anaconda.com/pkgs/r/linux-32": ("defaults", 2),
                "https://repo.anaconda.com/pkgs/r/noarch": ("defaults", 2),
                "https://repo.anaconda.com/pkgs/msys2/new-optimized-subdir": (
                    "defaults",
                    3,
                ),
                "https://repo.anaconda.com/pkgs/msys2/linux-32": ("defaults", 3),
                "https://repo.anaconda.com/pkgs/msys2/noarch": ("defaults", 3),
                "https://conda.anaconda.org/conda-forge/new-optimized-subdir": (
                    "conda-forge",
                    4,
                ),
                "https://conda.anaconda.org/conda-forge/linux-32": ("conda-forge", 4),
                "https://conda.anaconda.org/conda-forge/noarch": ("conda-forge", 4),
            }
        else:
            assert channel_priority_map == {
                "https://conda.anaconda.org/conda-test/new-optimized-subdir": (
                    "conda-test",
                    0,
                ),
                "https://conda.anaconda.org/conda-test/linux-32": ("conda-test", 0),
                "https://conda.anaconda.org/conda-test/noarch": ("conda-test", 0),
                "https://repo.anaconda.com/pkgs/main/new-optimized-subdir": (
                    "defaults",
                    1,
                ),
                "https://repo.anaconda.com/pkgs/main/linux-32": ("defaults", 1),
                "https://repo.anaconda.com/pkgs/main/noarch": ("defaults", 1),
                "https://repo.anaconda.com/pkgs/r/new-optimized-subdir": (
                    "defaults",
                    2,
                ),
                "https://repo.anaconda.com/pkgs/r/linux-32": ("defaults", 2),
                "https://repo.anaconda.com/pkgs/r/noarch": ("defaults", 2),
                "https://conda.anaconda.org/conda-forge/new-optimized-subdir": (
                    "conda-forge",
                    3,
                ),
                "https://conda.anaconda.org/conda-forge/linux-32": ("conda-forge", 3),
                "https://conda.anaconda.org/conda-forge/noarch": ("conda-forge", 3),
            }


def test_ppc64le_vs_ppc64():
    Channel._cache_.clear()

    ppc64_channel = Channel("https://conda.anaconda.org/dummy-channel/linux-ppc64")
    assert ppc64_channel.subdir == "linux-ppc64"
    assert (
        ppc64_channel.url(with_credentials=True)
        == "https://conda.anaconda.org/dummy-channel/linux-ppc64"
    )

    ppc64le_channel = Channel("https://conda.anaconda.org/dummy-channel/linux-ppc64le")
    assert ppc64le_channel.subdir == "linux-ppc64le"
    assert (
        ppc64le_channel.url(with_credentials=True)
        == "https://conda.anaconda.org/dummy-channel/linux-ppc64le"
    )
    print(Channel._cache_)
    Channel._cache_.clear()

    ppc64le_channel = Channel("https://conda.anaconda.org/dummy-channel/linux-ppc64le")
    assert ppc64le_channel.subdir == "linux-ppc64le"
    assert (
        ppc64le_channel.url(with_credentials=True)
        == "https://conda.anaconda.org/dummy-channel/linux-ppc64le"
    )

    ppc64_channel = Channel("https://conda.anaconda.org/dummy-channel/linux-ppc64")
    assert ppc64_channel.subdir == "linux-ppc64"
    assert (
        ppc64_channel.url(with_credentials=True)
        == "https://conda.anaconda.org/dummy-channel/linux-ppc64"
    )


def test_channel_mangles_urls():
    """
    CondaSession() runs urls through Channel, and cannot be used to fetch files
    with unknown extensions (it will mangle the URL)
    """
    reset_context()
    cases = [
        (
            "https://conda.anaconda.org/conda-forge/linux-64/repodata.json",
            "https://conda.anaconda.org/conda-forge/linux-64",
        ),
        (
            "https://conda.anaconda.org/conda-forge/linux-64/repodata.jlap",
            "https://conda.anaconda.org/conda-forge/linux-64",
        ),
        # This strange behavior may need to change:
        (
            "https://conda.anaconda.org/conda-forge/linux-64/repodata.json.bz2",
            "https://conda.anaconda.org/conda-forge/repodata.json.bz2/linux-64",
        ),
    ]

    for url, expected in cases:
        assert str(Channel(url)) == expected
