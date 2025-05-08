# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.base.constants import CONDA_PACKAGE_EXTENSION_V1, CONDA_PACKAGE_EXTENSION_V2
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.cli.common import arg2spec, spec_from_line
from conda.common.compat import on_win
from conda.common.io import env_unmodified
from conda.exceptions import CondaValueError, InvalidMatchSpec, InvalidSpec
from conda.models.channel import Channel
from conda.models.dist import Dist
from conda.models.match_spec import ChannelMatch, MatchSpec, _parse_spec_str
from conda.models.records import PackageRecord
from conda.models.version import VersionSpec

blas_value = "accelerate" if context.subdir == "osx-64" else "openblas"


def m(string):
    return str(MatchSpec(string))


def DPkg(s, **kwargs):
    d = Dist(s)
    return PackageRecord(
        fn=d.to_filename(),
        name=d.name,
        version=d.version,
        build=d.build_string,
        build_number=int(d.build_string.rsplit("_", 1)[-1]),
        channel=d.channel,
        subdir=context.subdir,
        md5="012345789",
        **kwargs,
    )


@pytest.mark.benchmark
def test_match_1():
    for spec, result in (
        ("numpy 1.7*", True),
        ("numpy 1.7.1", True),
        ("numpy 1.7", False),
        ("numpy 1.5*", False),
        ("numpy >=1.5", True),
        ("numpy >=1.5,<2", True),
        ("numpy >=1.8,<1.9", False),
        ("numpy >1.5,<2,!=1.7.1", False),
        ("numpy >1.8,<2|==1.7", False),
        ("numpy >1.8,<2|>=1.7.1", True),
        ("numpy >=1.8|1.7*", True),
        ("numpy ==1.7", False),
        ("numpy >=1.5,>1.6", True),
        ("numpy ==1.7.1", True),
        ("numpy ==1.7.1.0", True),
        ("numpy==1.7.1.0.0", True),
        ("numpy >=1,*.7.*", True),
        ("numpy *.7.*,>=1", True),
        ("numpy >=1,*.8.*", False),
        ("numpy >=2,*.7.*", False),
        ("numpy 1.6*|1.7*", True),
        ("numpy 1.6*|1.8*", False),
        ("numpy 1.6.2|1.7*", True),
        ("numpy 1.6.2|1.7.1", True),
        ("numpy 1.6.2|1.7.0", False),
        ("numpy 1.7.1 py27_0", True),
        ("numpy 1.7.1 py26_0", False),
        ("numpy >1.7.1a", True),
        ("python", False),
    ):
        m = MatchSpec(spec)
        assert m.match(DPkg("numpy-1.7.1-py27_0.tar.bz2")) == result
        assert "name" in m
        assert m.name == "python" or "version" in m

    # both version numbers conforming to PEP 440
    assert not MatchSpec("numpy >=1.0.1").match(DPkg("numpy-1.0.1a-0.tar.bz2"))
    # both version numbers non-conforming to PEP 440
    assert not MatchSpec("numpy >=1.0.1.vc11").match(
        DPkg("numpy-1.0.1a.vc11-0.tar.bz2")
    )
    assert MatchSpec("numpy >=1.0.1*.vc11").match(DPkg("numpy-1.0.1a.vc11-0.tar.bz2"))
    # one conforming, other non-conforming to PEP 440
    assert MatchSpec("numpy <1.0.1").match(DPkg("numpy-1.0.1.vc11-0.tar.bz2"))
    assert MatchSpec("numpy <1.0.1").match(DPkg("numpy-1.0.1a.vc11-0.tar.bz2"))
    assert not MatchSpec("numpy >=1.0.1.vc11").match(DPkg("numpy-1.0.1a-0.tar.bz2"))
    assert MatchSpec("numpy >=1.0.1a").match(DPkg("numpy-1.0.1z-0.tar.bz2"))
    assert MatchSpec("numpy >=1.0.1a py27*").match(DPkg("numpy-1.0.1z-py27_1.tar.bz2"))
    assert MatchSpec("blas * openblas_0").match(DPkg("blas-1.0-openblas_0.tar.bz2"))

    assert MatchSpec("blas")._is_simple()
    assert not MatchSpec("blas 1.0")._is_simple()
    assert not MatchSpec("blas 1.0 1")._is_simple()

    m = MatchSpec("blas 1.0", optional=True)
    m2 = MatchSpec(m, optional=False)
    m3 = MatchSpec(m2, target="blas-1.0-0.tar.bz2")
    m4 = MatchSpec(m3, target=None, optional=True)
    assert m.spec == m2.spec and m.optional != m2.optional
    assert m2.spec == m3.spec and m2.optional == m3.optional and m2.target != m3.target
    assert m == m4

    with pytest.raises(ValueError):
        MatchSpec((1, 2, 3))


def test_no_name_match_spec():
    ms = MatchSpec(track_features="mkl")
    assert str(ms) == "*[track_features=mkl]"


def test_to_filename():
    m1 = MatchSpec(fn="foo-1.7-52.tar.bz2")
    m2 = MatchSpec(name="foo", version="1.7", build="52")
    m3 = MatchSpec(Dist("defaults::foo-1.7-52"))
    assert m1._to_filename_do_not_use() == "foo-1.7-52.tar.bz2"
    assert m2._to_filename_do_not_use() == "foo-1.7-52.tar.bz2"
    assert m3._to_filename_do_not_use() == "foo-1.7-52.tar.bz2"

    for spec in "bitarray", "pycosat 0.6.0", "numpy 1.6*":
        ms = MatchSpec(spec)
        assert ms._to_filename_do_not_use() is None


def test_hash():
    a = MatchSpec("numpy 1.7*")
    b = MatchSpec("numpy 1.7*")
    c = MatchSpec(name="numpy", version="1.7*")
    # optional should not change the hash
    d = MatchSpec(c, optional=True)
    assert d.optional
    assert not c.optional
    assert a is not b
    assert a is not c
    assert a is not d
    assert a == b
    assert a == c
    assert a != d
    assert hash(a) == hash(b)
    assert hash(a) == hash(c)
    assert hash(a) != hash(d)
    c = MatchSpec("python")
    d = MatchSpec("python 2.7.4")
    e = MatchSpec("python", version="2.7.4")
    f = MatchSpec("* 2.7.4", name="python")
    assert d == e
    assert d == f
    assert a != c
    assert hash(a) != hash(c)
    assert c != d
    assert hash(c) != hash(d)


def test_canonical_string_forms():
    assert m("numpy") == "numpy"

    assert m("numpy=1.7") == "numpy=1.7"
    assert m("numpy 1.7*") == "numpy=1.7"
    assert m("numpy 1.7.*") == "numpy=1.7"
    assert m("numpy[version='1.7*']") == "numpy=1.7"
    assert m("numpy[version='1.7.*']") == "numpy=1.7"
    assert m("numpy[version=1.7.*]") == "numpy=1.7"

    assert m("numpy==1.7") == "numpy==1.7"
    assert m("numpy[version='1.7']") == "numpy==1.7"
    assert m("numpy[version=1.7]") == "numpy==1.7"
    assert m("numpy 1.7") == "numpy==1.7"

    assert m("numpy[version='1.7|1.8']") == "numpy[version='1.7|1.8']"
    assert m('numpy[version="1.7,1.8"]') == "numpy[version='1.7,1.8']"
    assert m("numpy >1.7") == "numpy[version='>1.7']"
    assert m("numpy>=1.7") == "numpy[version='>=1.7']"

    assert m("numpy=1.7=py3*_2") == "numpy==1.7[build=py3*_2]"
    assert m("numpy=1.7.*=py3*_2") == "numpy=1.7[build=py3*_2]"

    assert m("https://repo.anaconda.com/pkgs/free::numpy") == "pkgs/free::numpy"
    assert m("numpy[channel=https://repo.anaconda.com/pkgs/free]") == "pkgs/free::numpy"
    assert m("defaults::numpy") == "defaults::numpy"
    assert m("numpy[channel=defaults]") == "defaults::numpy"
    assert m("conda-forge::numpy") == "conda-forge::numpy"
    assert m("numpy[channel=conda-forge]") == "conda-forge::numpy"

    assert m("numpy[channel=defaults,subdir=osx-64]") == "defaults/osx-64::numpy"
    assert (
        m("numpy[channel=https://repo.anaconda.com/pkgs/free/osx-64, subdir=linux-64]")
        == "pkgs/free/linux-64::numpy"
    )
    assert (
        m("https://repo.anaconda.com/pkgs/free/win-32::numpy")
        == "pkgs/free/win-32::numpy"
    )
    assert (
        m("numpy[channel=https://repo.anaconda.com/pkgs/free/osx-64]")
        == "pkgs/free/osx-64::numpy"
    )
    assert m("defaults/win-32::numpy") == "defaults/win-32::numpy"
    assert m("conda-forge/linux-64::numpy") == "conda-forge/linux-64::numpy"
    assert m("numpy[channel=conda-forge,subdir=noarch]") == "conda-forge/noarch::numpy"

    assert m("numpy[subdir=win-32]") == "numpy[subdir=win-32]"
    assert m("*/win-32::numpy") == "numpy[subdir=win-32]"
    assert m('*/win-32::numpy[subdir="osx-64"]') == "numpy[subdir=osx-64]"

    # TODO: should the result in these example pull out subdir?
    assert (
        m("https://repo.anaconda.com/pkgs/free/linux-32::numpy")
        == "pkgs/free/linux-32::numpy"
    )
    assert (
        m("numpy[channel=https://repo.anaconda.com/pkgs/free/linux-32]")
        == "pkgs/free/linux-32::numpy"
    )

    assert m("numpy=1.10=py38_0") == "numpy==1.10=py38_0"
    assert m("numpy==1.10=py38_0") == "numpy==1.10=py38_0"
    assert m("numpy[version=1.10 build=py38_0]") == "numpy==1.10=py38_0"

    assert m("numpy!=1.10") == "numpy!=1.10"
    assert m("numpy !=1.10") == "numpy!=1.10"
    assert m("numpy!=1.10 py38_0") == "numpy[version='!=1.10',build=py38_0]"
    assert m("numpy !=1.10 py38_0") == "numpy[version='!=1.10',build=py38_0]"
    assert m("numpy!=1.10=py38_0") == "numpy[version='!=1.10',build=py38_0]"
    assert m("numpy !=1.10=py38_0") == "numpy[version='!=1.10',build=py38_0]"
    assert m("numpy >1.7,!=1.10 py38_0") == "numpy[version='>1.7,!=1.10',build=py38_0]"
    assert m("numpy!=1.10.*") == "numpy!=1.10.*"
    assert m("numpy!=1.10,!=1.11") == "numpy[version='!=1.10,!=1.11']"
    assert m("numpy=1.10.*,!=1.10.2") == "numpy[version='=1.10.*,!=1.10.2']"

    assert m("numpy ~=1.10.1") == "numpy~=1.10.1"
    assert m("numpy~=1.10.1") == "numpy~=1.10.1"
    assert m("numpy ~=1.10.1 py38_0") == "numpy[version='~=1.10.1',build=py38_0]"

    assert m("openssl=1.1.1_") == "openssl=1.1.1_"
    assert m("openssl>=1.1.1_,!=1.1.1c") == "openssl[version='>=1.1.1_,!=1.1.1c']"

    # # a full, exact spec looks like 'defaults/linux-64::numpy==1.8=py26_0'
    # # can we take an old dist str and reliably parse it with MatchSpec?
    # assert m("numpy-1.10-py38_0") == "numpy==1.10=py38_0"
    # assert m("numpy-1.10-py38_0[channel=defaults]") == "defaults::numpy==1.10=py38_0"
    # assert m("*/win-32::numpy-1.10-py38_0[channel=defaults]") == "defaults/win-32::numpy==1.10=py38_0"


@pytest.mark.skip(reason="key-value features interface has been disabled in conda 4.4")
def test_key_value_features_canonical_string_forms():
    assert (
        m("numpy[build=py3*_2, track_features=mkl]")
        == "numpy[build=py3*_2,provides_features='blas=mkl']"
    )
    assert (
        m("numpy[build=py3*_2, track_features='mkl debug']")
        == "numpy[build=py3*_2,provides_features='blas=mkl debug=true']"
    )
    assert (
        m("numpy[track_features='mkl,debug', build=py3*_2]")
        == "numpy[build=py3*_2,provides_features='blas=mkl debug=true']"
    )
    assert (
        m("numpy[track_features='mkl,debug' build=py3*_2]")
        == "numpy[build=py3*_2,provides_features='blas=mkl debug=true']"
    )

    assert (
        m('numpy[features="mkl debug" build_number=2]')
        == "numpy[build_number=2,provides_features='blas=mkl debug=true']"
    )


def test_legacy_features_canonical_string_forms():
    assert m("mkl@") == "*[track_features=mkl]"

    # assert m("@mkl") == "*[features=mkl]"
    assert str(MatchSpec(features="mkl")) == "*[features=mkl]"


def test_tarball_match_specs():
    url = "https://conda.anaconda.org/conda-canary/linux-64/conda-4.3.21.post699+1dab973-py36h4a561cd_0.tar.bz2"
    assert (
        m(url) == "conda-canary/linux-64::conda==4.3.21.post699+1dab973=py36h4a561cd_0"
    )
    assert (
        m("conda-canary/linux-64::conda==4.3.21.post699+1dab973=py36h4a561cd_0")
        == "conda-canary/linux-64::conda==4.3.21.post699+1dab973=py36h4a561cd_0"
    )

    url = "https://conda.anaconda.org/conda-canary/conda-4.3.21.post699+1dab973-py36h4a561cd_0.tar.bz2"
    assert m(url) == f"*[url={url}]"

    pref1 = PackageRecord(
        channel=Channel(None),
        name="conda",
        version="4.3.21.post699+1dab973",
        build="py36h4a561cd_0",
        build_number=0,
        fn="conda-4.3.21.post699+1dab973-py36h4a561cd_0.tar.bz2",
        url=url,
    )
    pref2 = PackageRecord.from_objects(pref1, md5="1234")
    assert MatchSpec(url=url).match(pref1)
    assert MatchSpec(m(url)).match(pref1)
    assert MatchSpec(m(url)).match(pref1.dump())
    assert not MatchSpec(url=url, md5="1234").match(pref1)
    assert not MatchSpec(url=url, md5="1234").match(pref1.dump())
    assert MatchSpec(url=url, md5="1234").match(pref2)
    assert MatchSpec(url=url, md5="1234").get("md5") == "1234"

    url = "file:///var/folders/cp/7r2s_s593j7_cpdtxxsmct880000gp/T/edfc ñçêáôß/flask-0.10.1-py35_2.tar.bz2"
    assert m(url) == f"*[url='{url}']"
    # url = '*[url="file:///var/folders/cp/7r2s_s593j7_cpdtxxsmct880000gp/T/edfc ñçêáôß/flask-0.10.1-py35_2.tar.bz2"]'

    # TODO: we need this working correctly with both channel and subdir
    # especially for usages around PrefixData.all_subdir_urls() and Solver._prepare()
    # assert MatchSpec('defaults/zos::python').get_exact_value('channel').urls() == ()


def test_url_percent_encoding():
    """
    More info here: https://github.com/mamba-org/mamba/issues/3737
    """
    # x264 version has an epoch "1!164"; ! is encoded as %21
    url_with = (
        "https://anaconda.org/conda-forge/linux-64/x264-1%21164.3095-h166bdaf_2.tar.bz2"
    )
    url_without = (
        "https://anaconda.org/conda-forge/linux-64/x264-1!164.3095-h166bdaf_2.tar.bz2"
    )

    assert MatchSpec(url_with).version == MatchSpec(url_without).version

    # Ficticious channel that yells at you
    url_with = "https://anaconda.org/conda-forge%21/linux-64/x264-1%21164.3095-h166bdaf_2.tar.bz2"
    url_without = (
        "https://anaconda.org/conda-forge!/linux-64/x264-1!164.3095-h166bdaf_2.tar.bz2"
    )

    assert (
        MatchSpec(url_with).get("channel").name
        == MatchSpec(url_without).get("channel").name
    )


def test_exact_values():
    assert MatchSpec("*").get_exact_value("name") is None
    assert MatchSpec("numpy").get_exact_value("name") == "numpy"

    assert MatchSpec("numpy=1.7").get_exact_value("version") is None
    assert MatchSpec("numpy==1.7").get_exact_value("version") == "1.7"
    assert MatchSpec("numpy[version=1.7]").get_exact_value("version") == "1.7"

    assert MatchSpec("numpy=1.7=py3*_2").get_exact_value("version") == "1.7"
    assert MatchSpec("numpy=1.7=py3*_2").get_exact_value("build") is None
    assert MatchSpec("numpy=1.7=py3*_2").get_exact_value("version") == "1.7"
    assert MatchSpec("numpy=1.7=py3*_2").get_exact_value("build") is None
    assert MatchSpec("numpy=1.7.*=py37_2").get_exact_value("version") is None
    assert MatchSpec("numpy=1.7.*=py37_2").get_exact_value("build") == "py37_2"


def test_channel_matching():
    with env_unmodified(conda_tests_ctxt_mgmt_def_pol):
        assert ChannelMatch("pkgs/main").match("defaults") is False
        assert ChannelMatch("defaults").match("pkgs/main") is True

        assert (
            ChannelMatch("https://repo.anaconda.com/pkgs/main").match("defaults")
            is False
        )
        assert (
            ChannelMatch("defaults").match("https://repo.anaconda.com/pkgs/main")
            is True
        )

        assert (
            ChannelMatch("https://conda.anaconda.org/conda-forge").match("conda-forge")
            is True
        )
        assert (
            ChannelMatch("conda-forge").match("https://conda.anaconda.org/conda-forge")
            is True
        )

        assert (
            ChannelMatch("https://repo.anaconda.com/pkgs/main").match("conda-forge")
            is False
        )

        assert str(MatchSpec("pkgs/main::*")) == "pkgs/main::*"
        assert str(MatchSpec("defaults::*")) == "defaults::*"


def test_matchspec_errors():
    with pytest.raises(InvalidSpec):
        MatchSpec("blas [optional")

    with pytest.raises(InvalidSpec):
        MatchSpec("blas [test=]")

    with pytest.raises(InvalidSpec):
        MatchSpec('blas[invalid="1"]')

    if not on_win:
        # skipping on Windows for now.  don't feel like dealing with the windows url path crud
        assert (
            str(MatchSpec("/some/file/on/disk/package-1.2.3-2.tar.bz2"))
            == "*[url=file:///some/file/on/disk/package-1.2.3-2.tar.bz2]"
        )


def test_dist():
    with env_unmodified(conda_tests_ctxt_mgmt_def_pol):
        dst = Dist("defaults::foo-1.2.3-4.tar.bz2")
        a = MatchSpec(dst)
        b = MatchSpec(a)
        c = MatchSpec(dst, optional=True, target="burg")
        d = MatchSpec(a, build="5")

        assert a == b
        assert hash(a) == hash(b)
        assert a is b

        assert a != c
        assert hash(a) != hash(c)

        assert a != d
        assert hash(a) != hash(d)

        p = MatchSpec(channel="defaults", name="python", version=VersionSpec("3.5*"))
        assert p.match(
            Dist(
                channel="defaults",
                dist_name="python-3.5.3-1",
                name="python",
                version="3.5.3",
                build_string="1",
                build_number=1,
                base_url=None,
                platform=None,
            )
        )

        assert not p.match(
            Dist(
                channel="defaults",
                dist_name="python-3.6.0-0",
                name="python",
                version="3.6.0",
                build_string="0",
                build_number=0,
                base_url=None,
                platform=None,
            )
        )

        assert p.match(
            Dist(
                channel="defaults",
                dist_name="python-3.5.1-0",
                name="python",
                version="3.5.1",
                build_string="0",
                build_number=0,
                base_url=None,
                platform=None,
            )
        )
        assert p.match(
            PackageRecord(
                name="python",
                version="3.5.1",
                build="0",
                build_number=0,
                depends=(
                    "openssl 1.0.2*",
                    "readline 6.2*",
                    "sqlite",
                    "tk 8.5*",
                    "xz 5.0.5",
                    "zlib 1.2*",
                    "pip",
                ),
                channel=Channel(
                    scheme="https",
                    auth=None,
                    location="repo.anaconda.com",
                    token=None,
                    name="pkgs/main",
                    platform="osx-64",
                    package_filename=None,
                ),
                subdir="osx-64",
                fn="python-3.5.1-0.tar.bz2",
                md5="a813bc0a32691ab3331ac9f37125164c",
                size=14678857,
                priority=0,
                url="https://repo.anaconda.com/pkgs/main/osx-64/python-3.5.1-0.tar.bz2",
            )
        )


def test_index_record():
    dst = Dist("defaults::foo-1.2.3-4.tar.bz2")
    rec = DPkg(dst)
    a = MatchSpec(dst)
    b = MatchSpec(rec)
    assert b.match(rec.dump())
    assert b.match(rec)
    assert a.match(rec)


def test_strictness():
    assert MatchSpec("foo").strictness == 1
    assert MatchSpec("foo 1.2").strictness == 2
    assert MatchSpec("foo 1.2 3").strictness == 3
    assert MatchSpec("foo 1.2 3 [channel=burg]").strictness == 3
    # Seems odd, but this is needed for compatibility
    assert MatchSpec("test* 1.2").strictness == 3
    assert MatchSpec("foo", build_number=2).strictness == 3


def test_build_number_and_filename():
    ms = MatchSpec("zlib 1.2.7 0")
    assert ms.get_exact_value("name") == "zlib"
    assert ms.get_exact_value("version") == "1.2.7"
    assert ms.get_exact_value("build") == "0"
    assert ms._to_filename_do_not_use() == "zlib-1.2.7-0.tar.bz2"


def test_openssl_match():
    dst = Dist("defaults::openssl-1.0.1_-4")
    assert MatchSpec("openssl>=1.0.1_").match(DPkg(dst))
    assert not MatchSpec("openssl>=1.0.1").match(DPkg(dst))


def test_track_features_match():
    dst = Dist("defaults::foo-1.2.3-4.tar.bz2")
    a = MatchSpec(features="test")
    assert str(a) == "*[features=test]"
    assert not a.match(DPkg(dst))
    assert not a.match(DPkg(dst, track_features=""))

    a = MatchSpec(track_features="test")
    assert a.match(DPkg(dst, track_features="test"))
    assert not a.match(DPkg(dst, track_features="test2"))
    assert not a.match(DPkg(dst, track_features="test me"))
    assert not a.match(DPkg(dst, track_features="you test"))
    assert not a.match(DPkg(dst, track_features="you test me"))
    assert a.get_exact_value("track_features") == frozenset(("test",))

    b = MatchSpec(track_features="mkl")
    assert not b.match(DPkg(dst))
    assert b.match(DPkg(dst, track_features="mkl"))
    assert b.match(DPkg(dst, track_features="mkl"))
    assert not b.match(DPkg(dst, track_features="mkl debug"))
    assert not b.match(DPkg(dst, track_features="debug"))

    c = MatchSpec(track_features="nomkl")
    assert not c.match(DPkg(dst))
    assert not c.match(DPkg(dst, track_features="mkl"))
    assert c.match(DPkg(dst, track_features="nomkl"))
    assert not c.match(DPkg(dst, track_features="nomkl debug"))

    # regression test for #6860
    d = MatchSpec(track_features="")
    assert d.get_exact_value("track_features") == frozenset()
    d = MatchSpec(track_features=" ")
    assert d.get_exact_value("track_features") == frozenset()
    d = MatchSpec(track_features=("", ""))
    assert d.get_exact_value("track_features") == frozenset()
    d = MatchSpec(track_features=("", "", "test"))
    assert d.get_exact_value("track_features") == frozenset(("test",))


def test_bracket_matches():
    record = {
        "name": "numpy",
        "version": "1.11.0",
        "build": "py34_7",
        "build_number": 7,
    }

    assert MatchSpec("numpy<2").match(record)
    assert MatchSpec("numpy[version<2]").match(record)
    assert not MatchSpec("numpy>2").match(record)
    assert not MatchSpec("numpy[version='>2']").match(record)

    assert MatchSpec("numpy[build_number='7']").match(record)
    assert MatchSpec("numpy[build_number='<8']").match(record)
    assert not MatchSpec("numpy[build_number='>7']").match(record)
    assert MatchSpec("numpy[build_number='>=7']").match(record)

    assert MatchSpec("numpy ~=1.10").match(record)
    assert MatchSpec("numpy~=1.10").match(record)


def test_license_match():
    record = {
        "name": "numpy",
        "version": "1.11.0",
        "build": "py34_7",
        "build_number": 7,
        "license": "LGPLv3+",
        "license_family": "LGPL",
    }
    assert MatchSpec("*[license_family='LGPL']").match(record)
    assert MatchSpec("*[license_family='lgpl']").match(record)
    assert MatchSpec("*[license_family='*GP*']").match(record)
    assert MatchSpec("*[license_family='*gp*']").match(record)
    assert MatchSpec("*[license_family='*GPL*']").match(record)
    assert MatchSpec("*[license_family='*gpl*']").match(record)

    assert MatchSpec("*[license='*gpl*']").match(record)
    assert MatchSpec("*[license='*v3+']").match(record)


def test_simple():
    assert arg2spec("python") == "python"
    assert arg2spec("python=2.6") == "python=2.6"
    assert arg2spec("python=2.6*") == "python=2.6"
    assert arg2spec("ipython=0.13.2") == "ipython=0.13.2"
    assert arg2spec("ipython=0.13.0") == "ipython=0.13.0"
    assert arg2spec("ipython==0.13.0") == "ipython==0.13.0"
    assert arg2spec("foo=1.3.0=3") == "foo==1.3.0=3"


def test_pip_style():
    assert arg2spec("foo>=1.3") == "foo[version='>=1.3']"
    assert arg2spec("zope.int>=1.3,<3.0") == "zope.int[version='>=1.3,<3.0']"
    assert arg2spec("numpy >=1.9") == "numpy[version='>=1.9']"


def test_invalid_arg2spec():
    with pytest.raises(CondaValueError):
        arg2spec("!xyz 1.3")


def cb_form(spec_str):
    return MatchSpec(spec_str).conda_build_form()


def test_invalid():
    assert spec_from_line("=") is None
    assert spec_from_line("foo 1.0") is None


def test_comment():
    assert spec_from_line("foo # comment") == "foo" == cb_form("foo # comment")
    assert spec_from_line("foo ## comment") == "foo" == cb_form("foo ## comment")


def test_conda_style():
    assert spec_from_line("foo") == "foo" == cb_form("foo")
    assert spec_from_line("foo=1.0=2") == "foo 1.0 2" == cb_form("foo=1.0=2")

    # assert spec_from_line('foo=1.0*') == 'foo 1.0.*' == cb_form('foo=1.0*')
    # assert spec_from_line('foo=1.0|1.2') == 'foo 1.0|1.2' == cb_form('foo=1.0|1.2')
    # assert spec_from_line('foo=1.0') == 'foo 1.0' == cb_form('foo=1.0')


def test_pip_style2():
    assert spec_from_line("foo>=1.0") == "foo >=1.0" == cb_form("foo>=1.0")
    assert spec_from_line("foo >=1.0") == "foo >=1.0" == cb_form("foo >=1.0")
    assert (
        spec_from_line("FOO-Bar >=1.0") == "foo-bar >=1.0" == cb_form("FOO-Bar >=1.0")
    )
    assert spec_from_line("foo >= 1.0") == "foo >=1.0" == cb_form("foo >= 1.0")
    assert spec_from_line("foo > 1.0") == "foo >1.0" == cb_form("foo > 1.0")
    assert spec_from_line("foo != 1.0") == "foo !=1.0" == cb_form("foo != 1.0")
    assert spec_from_line("foo <1.0") == "foo <1.0" == cb_form("foo <1.0")
    assert (
        spec_from_line("foo >=1.0 , < 2.0")
        == "foo >=1.0,<2.0"
        == cb_form("foo >=1.0 , < 2.0")
    )


def test_parse_spec_str_tarball_url():
    with env_unmodified(conda_tests_ctxt_mgmt_def_pol):
        url = "https://repo.anaconda.com/pkgs/main/linux-64/_license-1.1-py27_1.tar.bz2"
        assert _parse_spec_str(url) == {
            "channel": "defaults",
            "subdir": "linux-64",
            "name": "_license",
            "version": "1.1",
            "build": "py27_1",
            "fn": "_license-1.1-py27_1.tar.bz2",
            "url": url,
        }

        url = "https://conda.anaconda.org/conda-canary/linux-64/conda-4.3.21.post699+1dab973-py36h4a561cd_0.tar.bz2"
        assert _parse_spec_str(url) == {
            "channel": "conda-canary",
            "subdir": "linux-64",
            "name": "conda",
            "version": "4.3.21.post699+1dab973",
            "build": "py36h4a561cd_0",
            "fn": "conda-4.3.21.post699+1dab973-py36h4a561cd_0.tar.bz2",
            "url": url,
        }

        url = "https://conda.anaconda.org/conda-canary/linux-64/conda-4.3.21.post699+1dab973-py36h4a561cd_0.conda"
        assert _parse_spec_str(url) == {
            "channel": "conda-canary",
            "subdir": "linux-64",
            "name": "conda",
            "version": "4.3.21.post699+1dab973",
            "build": "py36h4a561cd_0",
            "fn": "conda-4.3.21.post699+1dab973-py36h4a561cd_0.conda",
            "url": url,
        }


def test_parse_spec_str_no_brackets():
    assert _parse_spec_str("numpy") == {
        "_original_spec_str": "numpy",
        "name": "numpy",
    }
    # For whatever reason "numpy=" is allowed and will be interpreted as "numpy"
    assert _parse_spec_str("numpy=") == {
        "_original_spec_str": "numpy=",
        "name": "numpy",
    }
    assert _parse_spec_str("defaults::numpy") == {
        "_original_spec_str": "defaults::numpy",
        "channel": "defaults",
        "name": "numpy",
    }
    assert _parse_spec_str("https://repo.anaconda.com/pkgs/free::numpy") == {
        "_original_spec_str": "https://repo.anaconda.com/pkgs/free::numpy",
        "channel": "pkgs/free",
        "name": "numpy",
    }
    assert _parse_spec_str("defaults::numpy=1.8") == {
        "_original_spec_str": "defaults::numpy=1.8",
        "channel": "defaults",
        "name": "numpy",
        "version": "1.8*",
    }
    assert _parse_spec_str("defaults::numpy =1.8") == {
        "_original_spec_str": "defaults::numpy =1.8",
        "channel": "defaults",
        "name": "numpy",
        "version": "1.8*",
    }
    assert _parse_spec_str("defaults::numpy=1.8=py27_0") == {
        "_original_spec_str": "defaults::numpy=1.8=py27_0",
        "channel": "defaults",
        "name": "numpy",
        "version": "1.8",
        "build": "py27_0",
    }
    assert _parse_spec_str("defaults::numpy 1.8 py27_0") == {
        "_original_spec_str": "defaults::numpy 1.8 py27_0",
        "channel": "defaults",
        "name": "numpy",
        "version": "1.8",
        "build": "py27_0",
    }


def test_parse_spec_str_with_brackets():
    assert _parse_spec_str("defaults::numpy[channel=anaconda]") == {
        "_original_spec_str": "defaults::numpy[channel=anaconda]",
        "channel": "anaconda",
        "name": "numpy",
    }
    assert _parse_spec_str("defaults::numpy 1.8 py27_0[channel=anaconda]") == {
        "_original_spec_str": "defaults::numpy 1.8 py27_0[channel=anaconda]",
        "channel": "anaconda",
        "name": "numpy",
        "version": "1.8",
        "build": "py27_0",
    }
    assert _parse_spec_str(
        "defaults::numpy=1.8=py27_0 [channel=anaconda,version=1.9, build=3]"
    ) == {
        "_original_spec_str": "defaults::numpy=1.8=py27_0 [channel=anaconda,version=1.9, build=3]",
        "channel": "anaconda",
        "name": "numpy",
        "version": "1.9",
        "build": "3",
    }
    assert _parse_spec_str(
        "defaults::numpy=1.8=py27_0 [channel='anaconda',version=\">=1.8,<2|1.9\", build='3']"
    ) == {
        "_original_spec_str": "defaults::numpy=1.8=py27_0 [channel='anaconda',version=\">=1.8,<2|1.9\", build='3']",
        "channel": "anaconda",
        "name": "numpy",
        "version": ">=1.8,<2|1.9",
        "build": "3",
    }

    # Ensure 'name' within brackets can't override the name specified outside of brackets
    assert _parse_spec_str(
        "tensorflow[name=* version=* md5=253b922ecdb5a30884875948b8904983]"
    ) == {
        "_original_spec_str": "tensorflow[name=* version=* md5=253b922ecdb5a30884875948b8904983]",
        "name": "tensorflow",
        "version": "*",
        "md5": "253b922ecdb5a30884875948b8904983",
    }
    assert _parse_spec_str("tensorflow[name=pytorch]") == {
        "_original_spec_str": "tensorflow[name=pytorch]",
        "name": "tensorflow",
    }

    assert _parse_spec_str(
        "defaults::numpy=1.8=py27_0 [name=\"pytorch\" channel='anaconda',version=\">=1.8,<2|1.9\", build='3']"
    ) == {
        "_original_spec_str": "defaults::numpy=1.8=py27_0 [name=\"pytorch\" channel='anaconda',version=\">=1.8,<2|1.9\", build='3']",
        "channel": "anaconda",
        "name": "numpy",
        "version": ">=1.8,<2|1.9",
        "build": "3",
    }


def test_star_name():
    assert _parse_spec_str("* 2.7.4") == {
        "_original_spec_str": "* 2.7.4",
        "name": "*",
        "version": "2.7.4",
    }
    assert _parse_spec_str("* >=1.3 2") == {
        "_original_spec_str": "* >=1.3 2",
        "name": "*",
        "version": ">=1.3",
        "build": "2",
    }


def test_parse_equal_equal():
    assert _parse_spec_str("numpy==1.7") == {
        "_original_spec_str": "numpy==1.7",
        "name": "numpy",
        "version": "1.7",
    }
    assert _parse_spec_str("numpy ==1.7") == {
        "_original_spec_str": "numpy ==1.7",
        "name": "numpy",
        "version": "1.7",
    }
    assert _parse_spec_str("numpy=1.7") == {
        "_original_spec_str": "numpy=1.7",
        "name": "numpy",
        "version": "1.7*",
    }
    assert _parse_spec_str("numpy =1.7") == {
        "_original_spec_str": "numpy =1.7",
        "name": "numpy",
        "version": "1.7*",
    }
    assert _parse_spec_str("numpy !=1.7") == {
        "_original_spec_str": "numpy !=1.7",
        "name": "numpy",
        "version": "!=1.7",
    }


def test_parse_hard():
    assert _parse_spec_str("numpy~=1.7.1") == {
        "_original_spec_str": "numpy~=1.7.1",
        "name": "numpy",
        "version": "~=1.7.1",
    }
    assert _parse_spec_str("numpy>1.8,<2|==1.7") == {
        "_original_spec_str": "numpy>1.8,<2|==1.7",
        "name": "numpy",
        "version": ">1.8,<2|==1.7",
    }
    assert _parse_spec_str("numpy >1.8,<2|==1.7,!=1.9,~=1.7.1 py34_0") == {
        "_original_spec_str": "numpy >1.8,<2|==1.7,!=1.9,~=1.7.1 py34_0",
        "name": "numpy",
        "version": ">1.8,<2|==1.7,!=1.9,~=1.7.1",
        "build": "py34_0",
    }
    assert _parse_spec_str("*>1.8,<2|==1.7") == {
        "_original_spec_str": "*>1.8,<2|==1.7",
        "name": "*",
        "version": ">1.8,<2|==1.7",
    }
    assert _parse_spec_str("* >1.8,<2|==1.7") == {
        "_original_spec_str": "* >1.8,<2|==1.7",
        "name": "*",
        "version": ">1.8,<2|==1.7",
    }

    assert _parse_spec_str("* 1 *") == {
        "_original_spec_str": "* 1 *",
        "name": "*",
        "version": "1",
        "build": "*",
    }
    assert _parse_spec_str("* * openblas_0") == {
        "_original_spec_str": "* * openblas_0",
        "name": "*",
        "version": "*",
        "build": "openblas_0",
    }
    assert _parse_spec_str("* * *") == {
        "_original_spec_str": "* * *",
        "name": "*",
        "version": "*",
        "build": "*",
    }
    assert _parse_spec_str("* *") == {
        "_original_spec_str": "* *",
        "name": "*",
        "version": "*",
    }


def test_parse_errors():
    with pytest.raises(InvalidMatchSpec):
        _parse_spec_str("!xyz 1.3")


def test_parse_channel_subdir():
    assert _parse_spec_str("conda-forge::foo>=1.0") == {
        "_original_spec_str": "conda-forge::foo>=1.0",
        "channel": "conda-forge",
        "name": "foo",
        "version": ">=1.0",
    }

    assert _parse_spec_str("conda-forge/linux-32::foo>=1.0") == {
        "_original_spec_str": "conda-forge/linux-32::foo>=1.0",
        "channel": "conda-forge",
        "subdir": "linux-32",
        "name": "foo",
        "version": ">=1.0",
    }

    assert _parse_spec_str("*/linux-32::foo>=1.0") == {
        "_original_spec_str": "*/linux-32::foo>=1.0",
        "channel": "*",
        "subdir": "linux-32",
        "name": "foo",
        "version": ">=1.0",
    }


def test_parse_parens():
    assert _parse_spec_str("conda-forge::foo[build=3](target=blarg,optional)") == {
        "_original_spec_str": "conda-forge::foo[build=3](target=blarg,optional)",
        "channel": "conda-forge",
        "name": "foo",
        "build": "3",
        # "target": "blarg",  # suppressing these for now
        # "optional": True,
    }


def test_parse_build_number_brackets():
    assert _parse_spec_str("python[build_number=3]") == {
        "_original_spec_str": "python[build_number=3]",
        "name": "python",
        "build_number": "3",
    }
    assert _parse_spec_str("python[build_number='>3']") == {
        "_original_spec_str": "python[build_number='>3']",
        "name": "python",
        "build_number": ">3",
    }
    assert _parse_spec_str("python[build_number='>=3']") == {
        "_original_spec_str": "python[build_number='>=3']",
        "name": "python",
        "build_number": ">=3",
    }

    assert _parse_spec_str("python[build_number='<3']") == {
        "_original_spec_str": "python[build_number='<3']",
        "name": "python",
        "build_number": "<3",
    }
    assert _parse_spec_str("python[build_number='<=3']") == {
        "_original_spec_str": "python[build_number='<=3']",
        "name": "python",
        "build_number": "<=3",
    }

    # # these don't work right now, should they?
    # assert _parse_spec_str("python[build_number<3]") == {
    #     "name": "python",
    #     "build_number": '<3',
    # }
    # assert _parse_spec_str("python[build_number<=3]") == {
    #     "name": "python",
    #     "build_number": '<=3',
    # }

    # # these don't work right now, should they?
    # assert _parse_spec_str("python[build_number>3]") == {
    #     "name": "python",
    #     "build_number": '>3',
    # }
    # assert _parse_spec_str("python[build_number>=3]") == {
    #     "name": "python",
    #     "build_number": '>=3',
    # }


def test_dist_str():
    for ext in (CONDA_PACKAGE_EXTENSION_V1, CONDA_PACKAGE_EXTENSION_V2):
        m1 = MatchSpec.from_dist_str(f"anaconda/{context.subdir}::python-3.6.6-0{ext}")
        m2 = MatchSpec.from_dist_str(f"anaconda/{context.subdir}::python-3.6.6-0")
        m3 = MatchSpec.from_dist_str(
            f"https://someurl.org/anaconda/{context.subdir}::python-3.6.6-0{ext}"
        )
        m4 = MatchSpec.from_dist_str(f"python-3.6.6-0{ext}")
        m5 = MatchSpec.from_dist_str(
            f"https://someurl.org/anaconda::python-3.6.6-0{ext}"
        )

        pref = DPkg(f"anaconda::python-3.6.6-0{ext}")
        pref.url = f"https://someurl.org/anaconda/{context.subdir}"

        assert m1.match(pref)
        assert m2.match(pref)
        assert m3.match(pref)
        assert m4.match(pref)
        pref.url = "https://someurl.org/anaconda"

        pref_dict = {
            "name": "python",
            "version": "3.6.6",
            "build": "0",
            "build_number": 0,
            "channel": Channel("anaconda"),
            "fn": f"python-3.6.6-0{ext}",
            "md5": "012345789",
            "url": "https://someurl.org/anaconda",
        }
        assert m5.match(pref_dict)


def test_merge_single_name():
    specs = (
        MatchSpec("exact"),
        MatchSpec("exact 1.2.3 1"),
        MatchSpec("exact >1.0,<2"),
    )
    merged_specs = MatchSpec.merge(specs)
    print(merged_specs)
    assert len(merged_specs) == 1
    merged_spec = merged_specs[0]
    print(merged_spec)
    assert str(merged_spec) == "exact[version='1.2.3,>1.0,<2',build=1]"
    assert merged_spec.match(
        {
            "name": "exact",
            "version": "1.2.3",
            "build": "1",
            "build_number": 1,
        }
    )
    assert not merged_spec.match(
        {
            "name": "exact",
            "version": "1.2.2",
            "build": "1",
            "build_number": 1,
        }
    )

    specs = (MatchSpec("exact 1.2.3 1"), MatchSpec("exact 1.2.3 2"))
    with pytest.raises(ValueError):
        MatchSpec.merge(specs)

    merged_specs = MatchSpec.merge((MatchSpec("exact 1.2.3 1"),))
    assert len(merged_specs) == 1
    assert str(merged_specs[0]) == "exact==1.2.3=1"


def test_merge_multiple_name():
    specs = tuple(
        MatchSpec(s)
        for s in (
            "exact",
            "exact 1.2.3 1",
            "bounded >=1.0,<2.0",
            "bounded >=1.5",
            "bounded <=1.8",
            "exact >1.0,<2",
        )
    )
    merged_specs = MatchSpec.merge(specs)
    print(merged_specs)
    assert len(merged_specs) == 2

    exact_spec = next(s for s in merged_specs if s.name == "exact")
    bounded_spec = next(s for s in merged_specs if s.name == "bounded")

    assert str(exact_spec) == "exact[version='1.2.3,>1.0,<2',build=1]"
    assert str(bounded_spec) == "bounded[version='<=1.8,>=1.0,<2.0,>=1.5']"

    assert not bounded_spec.match(
        {
            "name": "bounded",
            "version": "1",
            "build": "6",
            "build_number": 6,
        }
    )
    assert bounded_spec.match(
        {
            "name": "bounded",
            "version": "1.5",
            "build": "7",
            "build_number": 7,
        }
    )
    assert not bounded_spec.match(
        {
            "name": "bounded",
            "version": "2",
            "build": "8",
            "build_number": 8,
        }
    )


def test_channel_merge():
    specs = (MatchSpec("pkgs/main::python"), MatchSpec("defaults::python"))
    with pytest.raises(ValueError):
        MatchSpec.merge(specs)

    specs = (MatchSpec("defaults::python"), MatchSpec("pkgs/main::python"))
    with pytest.raises(ValueError):
        MatchSpec.merge(specs)

    specs = (MatchSpec("defaults::python"), MatchSpec("defaults::python 1.2.3"))
    merged = MatchSpec.merge(specs)
    assert len(merged) == 1
    assert str(merged[0]) == "defaults::python==1.2.3"

    specs = (MatchSpec("pkgs/free::python"), MatchSpec("pkgs/free::python 1.2.3"))
    merged = MatchSpec.merge(specs)
    assert len(merged) == 1
    assert str(merged[0]) == "pkgs/free::python==1.2.3"


def test_subdir_merge():
    specs = (
        MatchSpec("pkgs/main/linux-64::python"),
        MatchSpec("pkgs/main/linux-32::python"),
    )
    with pytest.raises(ValueError):
        MatchSpec.merge(specs)

    specs = (
        MatchSpec("defaults/win-32::python"),
        MatchSpec("defaults/win-64::python"),
    )
    with pytest.raises(ValueError):
        MatchSpec.merge(specs)

    specs = (
        MatchSpec("pkgs/free/linux-64::python"),
        MatchSpec("pkgs/free::python 1.2.3"),
    )
    merged = MatchSpec.merge(specs)
    assert len(merged) == 1
    assert str(merged[0]) == "pkgs/free/linux-64::python==1.2.3"
    assert merged[0] == MatchSpec(
        channel="pkgs/free", subdir="linux-64", name="python", version="1.2.3"
    )


def test_build_merge():
    specs = (
        MatchSpec("python[build=py27_1]"),
        MatchSpec("python=1.2.3=py27_1"),
        MatchSpec("conda-forge::python<=8"),
    )
    merged = MatchSpec.merge(specs)
    assert len(merged) == 1
    assert str(merged[0]) == "conda-forge::python[version='1.2.3,<=8',build=py27_1]"

    specs = (
        MatchSpec("python[build=py27_1]"),
        MatchSpec("python=1.2.3=1"),
        MatchSpec("conda-forge::python<=8[build=py27_1]"),
    )
    with pytest.raises(ValueError):
        MatchSpec.merge(specs)


def test_build_number_merge():
    specs = (
        MatchSpec("python[build_number=1]"),
        MatchSpec("python=1.2.3=py27_7"),
        MatchSpec("conda-forge::python<=8[build_number=1]"),
    )
    merged = MatchSpec.merge(specs)
    assert len(merged) == 1
    assert (
        str(merged[0])
        == "conda-forge::python[version='1.2.3,<=8',build=py27_7,build_number=1]"
    )

    specs = (
        MatchSpec("python[build_number=2]"),
        MatchSpec("python=1.2.3=py27_7"),
        MatchSpec("python<=8[build_number=1]"),
    )
    with pytest.raises(ValueError):
        MatchSpec.merge(specs)


def test_build_glob_merge():
    red = {
        "name": "my_pkg",
        "version": "1.17.3",
        "build": "red_habc123_3",
        "build_number": 3,
    }
    blue = {**red, "build": "blue_hdef1234_3"}

    no_build = MatchSpec("my_pkg=1.17.*")
    assert no_build.match(red)
    assert no_build.match(blue)

    red_prefix = MatchSpec("my_pkg=1.17.*=red_*")
    assert red_prefix.match(red)
    assert not red_prefix.match(blue)

    blue_prefix = MatchSpec("my_pkg=1.17.*=blue_*")
    assert not blue_prefix.match(red)
    assert blue_prefix.match(blue)

    blue_hash_prefix = MatchSpec("my_pkg=1.17.*=blue_hdef1234_*")
    assert not blue_hash_prefix.match(red)
    assert blue_hash_prefix.match(blue)

    red_exact = MatchSpec(f"my_pkg=1.17.*={red['build']}")
    assert red_exact.match(red)
    assert not red_exact.match(blue)

    red_scalar_wild = MatchSpec("my_pkg=1.17.*=*red*")
    assert red_scalar_wild.match(red)
    assert not red_scalar_wild.match(blue)

    merged, *unmergeable = MatchSpec.merge([red_scalar_wild, red_prefix])
    assert not unmergeable
    assert merged.match(red)
    # resulting build is the regex intersection
    assert merged.get("build") == "^(?=.*red.*)(?:red_.*)$"

    build_tail_2 = MatchSpec("my_pkg=1.17.*=*_2")
    build_tail_3 = MatchSpec("my_pkg=1.17.*=*_3")
    assert build_tail_3.match(red)
    assert build_tail_3.match(blue)

    hash_build_tail_3 = MatchSpec("my_pkg=1.17.*=*_habc123_3")
    assert hash_build_tail_3.match(red)
    assert not hash_build_tail_3.match(blue)

    merged, *unmergeable = MatchSpec.merge(
        [
            no_build,
            red_prefix,
        ]
    )
    assert not unmergeable
    assert merged.match(red)
    assert not merged.match(blue)

    merged, *unmergeable = MatchSpec.merge(
        [
            red_prefix,
            red_exact,
        ]
    )
    assert merged.get("build") == red_exact.get("build")
    assert merged.match(red)
    assert not merged.match(blue)

    merged, *unmergeable = MatchSpec.merge(
        [
            red_exact,
            red_prefix,
        ]
    )
    assert merged.get("build") == red_exact.get("build")
    assert merged.match(red)
    assert not merged.match(blue)

    # prefix + prefix, we keep the longest if compatible
    merged, *unmergeable = MatchSpec.merge(
        [
            blue_prefix,
            blue_hash_prefix,
        ]
    )
    assert merged.get("build") == blue_hash_prefix.get("build")
    assert merged.match(blue)
    assert not merged.match(red)

    # suffix + suffix, we keep the longest if compatible
    merged, *unmergeable = MatchSpec.merge(
        [
            build_tail_3,
            hash_build_tail_3,
        ]
    )
    assert merged.get("build") == hash_build_tail_3.get("build")
    assert merged.match(red)
    assert not merged.match(blue)

    merged, *unmergeable = MatchSpec.merge(
        [
            no_build,
            red_prefix,
            red_scalar_wild,
        ]
    )
    assert not unmergeable
    assert merged.match(red)
    assert not merged.match(blue)

    merged, *unmergeable = MatchSpec.merge(
        [
            no_build,
            red_prefix,
            red_scalar_wild,
            build_tail_3,
        ]
    )
    assert not unmergeable
    assert merged.match(red)
    assert not merged.match(blue)

    # definitely-incompatible combinations
    with pytest.raises(ValueError):
        MatchSpec.merge([red_exact, blue_prefix])

    with pytest.raises(ValueError):
        MatchSpec.merge([blue_prefix, red_exact])

    with pytest.raises(ValueError):
        MatchSpec.merge([blue_prefix, red_prefix])

    with pytest.raises(ValueError):
        MatchSpec.merge([build_tail_2, hash_build_tail_3])


def test_build_glob_merge_channel():
    no_channel = {
        "name": "my_pkg",
        "version": "1.17.3",
        "build": "pyhabc123_3",
        "build_number": 3,
    }
    exact_channel = {**no_channel, "channel": "conda-forge"}
    star_channel = {**no_channel, "channel": "conda-*"}
    non_matching_star_channel = {**no_channel, "channel": "*-adnoc"}

    merged, *unmergeable = MatchSpec.merge(
        [MatchSpec(spec) for spec in (no_channel, exact_channel, star_channel)]
    )
    assert not unmergeable
    assert merged.match(exact_channel)
    assert merged.get("channel") == exact_channel["channel"]

    with pytest.raises(ValueError):
        MatchSpec.merge(
            [MatchSpec(spec) for spec in (exact_channel, non_matching_star_channel)]
        )


@pytest.mark.parametrize("hash_type", ["md5", "sha256"])
def test_hash_merge_with_name(hash_type):
    specs = (
        MatchSpec(f"python[{hash_type}=deadbeef]"),
        MatchSpec("python=1.2.3"),
        MatchSpec(f"conda-forge::python[{hash_type}=deadbeef]"),
    )
    merged = MatchSpec.merge(specs)
    assert len(merged) == 1
    assert str(merged[0]) == f"conda-forge::python=1.2.3[{hash_type}=deadbeef]"

    specs = (
        MatchSpec(f"python[{hash_type}=FFBADD11]"),
        MatchSpec("python=1.2.3"),
        MatchSpec(f"python[{hash_type}=ffbadd11]"),
    )
    with pytest.raises(ValueError):
        MatchSpec.merge(specs)


@pytest.mark.parametrize("hash_type", ["md5", "sha256"])
def test_hash_merge_wo_name(hash_type):
    specs = (
        MatchSpec(f"*[{hash_type}=deadbeef]"),
        MatchSpec(f"*[{hash_type}=FFBADD11]"),
    )
    merged = MatchSpec.merge(specs)
    assert len(merged) == 2
    str_specs = (f"*[{hash_type}=deadbeef]", f"*[{hash_type}=FFBADD11]")
    assert str(merged[0]) in str_specs
    assert str(merged[1]) in str_specs
    assert str(merged[0]) != str(merged[1])


def test_catch_invalid_regexes():
    # Crashing case via fuzzing found via fuzzing. Reported here: https://github.com/conda/conda/issues/11999
    with pytest.raises(InvalidMatchSpec):
        MatchSpec("*/lin(ux-65::f/o>=>1y")
    # Inspired by above crasher
    with pytest.raises(InvalidMatchSpec):
        MatchSpec("^(aaaa$")


@pytest.mark.parametrize(
    "spec",
    (
        "pkg 4.2.2<6.0.0",
        "pkg>=0.10.0,<1.0.0<py312|>=0.13.0,<1.0.0>=py312",
    ),
)
def test_invalid_version_reports_spec(spec):
    with pytest.raises(InvalidMatchSpec) as exc:
        MatchSpec(spec)
    assert spec in str(exc.value)
