# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.core.prefix_data import PrefixData
from conda.testing.fixtures import (
    PYTHON_VERSION,
    TemplateEnvManager,
    clone_env,
    parse_python_spec,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch, Pytester

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpChannelFixture,
        TmpEnvFixture,
    )

pytest_plugins = ["conda.testing.fixtures", "pytester"]


def test_conda_cli(conda_cli: CondaCLIFixture) -> None:
    stdout, stderr, err = conda_cli("info")
    assert stdout
    assert not stderr
    assert not err


def test_session_conda_cli(session_conda_cli: CondaCLIFixture) -> None:
    stdout, stderr, err = session_conda_cli("info")
    assert not stdout
    assert not stderr
    assert not err


def test_path_factory(path_factory: PathFactoryFixture) -> None:
    path = path_factory()
    assert not path.exists()
    assert path.parent.is_dir()


def test_path_factory_name_mode(path_factory: PathFactoryFixture) -> None:
    """Test path_factory with explicit name (whole path component)."""
    positional = path_factory("myfile.txt")
    named = path_factory(name="myfile.txt")
    assert positional.name == named.name == "myfile.txt"
    assert not positional.exists()
    assert not named.exists()


@pytest.mark.parametrize(
    "prefix,infix,suffix",
    [
        pytest.param(None, None, None, id="no parts"),
        pytest.param("prefix-", None, None, id="prefix only"),
        pytest.param(None, "!", None, id="infix only"),
        pytest.param(None, None, ".suffix", id="suffix only"),
        pytest.param("prefix-", "infix", ".suffix", id="all parts"),
    ],
)
def test_path_factory_parts_mode(
    path_factory: PathFactoryFixture,
    prefix: str | None,
    infix: str | None,
    suffix: str | None,
) -> None:
    """Test path_factory with prefix/infix/suffix parameters triggers parts mode with UUID defaults."""
    path = path_factory(prefix=prefix, infix=infix, suffix=suffix)
    length = 0
    if prefix is None:
        length += 4  # UUID prefix
    else:
        assert prefix in path.name
        length += len(prefix)
    if infix is None:
        length += 4  # UUID suffix
    else:
        assert infix in path.name
        length += len(infix)
    if suffix is None:
        length += 4  # UUID suffix
    else:
        assert suffix in path.name
        length += len(suffix)
    assert len(path.name) == length


def test_path_factory_mutual_exclusivity(path_factory: PathFactoryFixture) -> None:
    """Test that name and parts params are mutually exclusive."""
    with pytest.raises(ValueError, match="mutually exclusive"):
        path_factory(name="myfile.txt", prefix="pre_")
    with pytest.raises(ValueError, match="mutually exclusive"):
        path_factory(name="myfile.txt", infix="!")
    with pytest.raises(ValueError, match="mutually exclusive"):
        path_factory(name="myfile.txt", suffix="_suf")


def test_path_factory_uniqueness(path_factory: PathFactoryFixture) -> None:
    """Test that multiple calls generate unique paths."""
    paths = [path_factory(infix="!") for _ in range(10)]
    assert len(set(paths)) == 10  # All unique


def test_tmp_env(tmp_env: TmpEnvFixture) -> None:
    with tmp_env() as prefix:
        assert PrefixData(prefix).is_environment()


@pytest.mark.parametrize(
    "name,path_prefix,path_infix,path_suffix",
    [
        pytest.param(None, None, None, None, id="no parts"),
        pytest.param("name", None, None, None, id="name only"),
        pytest.param(None, "prefix-", None, None, id="prefix only"),
        pytest.param(None, None, "env", None, id="infix only"),
        pytest.param(None, None, None, "-suffix", id="suffix only"),
        pytest.param(None, "prefix-", "env", "suffix", id="all parts"),
    ],
)
def test_tmp_env_path_parts(
    tmp_env: TmpEnvFixture,
    name: str | None,
    path_prefix: str | None,
    path_infix: str | None,
    path_suffix: str | None,
) -> None:
    """Test tmp_env with path_infix for special character testing."""
    with tmp_env(
        name=name,
        path_prefix=path_prefix,
        path_infix=path_infix,
        path_suffix=path_suffix,
        shallow=True,
    ) as prefix:
        if name is not None:
            assert prefix.name == name
        if path_prefix is not None:
            assert path_prefix in prefix.name
        if path_infix is not None:
            assert path_infix in prefix.name
        if path_suffix is not None:
            assert path_suffix in prefix.name
        assert PrefixData(prefix).is_environment()


def test_tmp_env_mutual_exclusivity(tmp_env: TmpEnvFixture) -> None:
    """Test that prefix, name, and path_* params are mutually exclusive."""
    with pytest.raises(ValueError, match="mutually exclusive"):
        with tmp_env(prefix="prefix", name="name"):
            pass
    with pytest.raises(ValueError, match="mutually exclusive"):
        with tmp_env(prefix="prefix", path_prefix="prefix"):
            pass
    with pytest.raises(ValueError, match="mutually exclusive"):
        with tmp_env(prefix="prefix", path_infix="infix"):
            pass
    with pytest.raises(ValueError, match="mutually exclusive"):
        with tmp_env(prefix="prefix", path_suffix="suffix"):
            pass


def test_empty_env(empty_env: Path) -> None:
    assert PrefixData(empty_env).is_environment()


def test_session_tmp_env(session_tmp_env: TmpEnvFixture) -> None:
    with session_tmp_env() as prefix:
        assert PrefixData(prefix).is_environment()


def test_env(pytester: Pytester) -> None:
    """Assert all tests get the same conda environment."""
    pytester.makepyfile(
        """
        import pytest

        pytest_plugins = "conda.testing.fixtures"

        @pytest.fixture
        def env1(tmp_env):
            with tmp_env() as prefix:
                yield prefix

        @pytest.fixture(scope="session")
        def env2(session_tmp_env):
            with session_tmp_env() as prefix:
                yield prefix

        @pytest.fixture(scope="session")
        def env3(session_tmp_env):
            with session_tmp_env() as prefix:
                yield prefix

        NAME = None

        def test_env1(env1):
            global NAME
            NAME = env1.name
            assert env1.name != "tmp_env-0"

        def test_env2(env1):
            assert env1.name != "tmp_env-0"
            assert env1.name != NAME

        def test_env3(env2):
            assert env2.name == "tmp_env-0"

        def test_env4(env2):
            assert env2.name == "tmp_env-0"

        def test_env5(env3):
            assert env3.name == "tmp_env-1"

        def test_env6(env3):
            assert env3.name == "tmp_env-1"
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=6)


def test_tmp_channel(tmp_channel: TmpChannelFixture) -> None:
    with tmp_channel() as (channel, url):
        assert channel.is_dir()


def test_monkeypatch(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_CLOBBER", "true")
    reset_context()
    assert context.clobber


def test_tmp_pkgs_dir(tmp_pkgs_dir: Path) -> None:
    assert tmp_pkgs_dir.is_dir()


def test_tmp_envs_dir(tmp_envs_dir: Path) -> None:
    assert tmp_envs_dir.is_dir()


def test_clone_env(path_factory: PathFactoryFixture) -> None:
    """Test the clone_env utility function."""
    # Create a source directory with some content
    source = path_factory(name="source_env")
    source.mkdir()
    (source / "conda-meta").mkdir()
    (source / "conda-meta" / "history").write_text("test")
    (source / "test_file.txt").write_text("hello")

    # Clone to target
    target = path_factory(name="target_env")
    assert clone_env(source, target)
    assert target.exists()
    assert (target / "conda-meta" / "history").read_text() == "test"
    assert (target / "test_file.txt").read_text() == "hello"


def test_clone_env_nonexistent_source(path_factory: PathFactoryFixture) -> None:
    """Test clone_env fails gracefully with nonexistent source."""
    source = path_factory(name="nonexistent")
    target = path_factory(name="target")
    # Should return False, not raise
    assert not clone_env(source, target)


def test_parse_python_spec() -> None:
    """Test the parse_python_spec utility function."""
    # Generic python spec
    assert parse_python_spec("python") == PYTHON_VERSION

    # Specific versions
    assert parse_python_spec("python=3.11") == "3.11"
    assert parse_python_spec("python==3.11") == "3.11"
    assert parse_python_spec("python>=3.10") == "3.10"
    assert parse_python_spec("python=3") == PYTHON_VERSION

    # Glob patterns (MatchSpec converts "python=3" to "3.*")
    assert parse_python_spec("python=3.11.*") == "3.11"

    # Patch versions should extract minor version
    assert parse_python_spec("python=3.11.5") == "3.11"
    assert parse_python_spec("python==3.10.12") == "3.10"

    # Non-python specs
    assert parse_python_spec("pip") is None
    assert parse_python_spec("numpy") is None

    # Invalid specs should return None
    assert parse_python_spec("") is None
    assert parse_python_spec("invalid[[[") is None


def test_template_env_manager(
    template_env_manager: TemplateEnvManager | None,
) -> None:
    """Test that template_env_manager fixture is available."""
    if template_env_manager is None:
        pytest.skip("Template environment manager creation failed")
    assert isinstance(template_env_manager, TemplateEnvManager)
    assert template_env_manager.base_path.exists()


def test_template_env_manager_find_matching_template(
    template_env_manager: TemplateEnvManager | None,
) -> None:
    """Test TemplateEnvManager.find_matching_template logic."""
    if template_env_manager is None:
        pytest.skip("Template environment manager not available")

    # Test Python-only spec - should create/return template with no delta
    template, delta = template_env_manager.find_matching_template(("python=3.11",))
    if template:  # Template creation might fail if Python 3.11 not available
        assert template.exists()
        assert delta == ()
        assert PrefixData(template).is_environment()

    # Test Python + pip - should create/return template with no delta
    template2, delta2 = template_env_manager.find_matching_template(
        ("python=3.11", "pip")
    )
    if template2:
        assert delta2 == ()

    # Test Python + other package - should return Python template with delta
    template3, delta3 = template_env_manager.find_matching_template(
        ("python=3.11", "numpy")
    )
    if template3:
        assert "numpy" in delta3

    # Test non-Python spec - should return None
    template4, delta4 = template_env_manager.find_matching_template(("zlib",))
    assert template4 is None
    assert delta4 == ("zlib",)

    # Test specs with flags - should return None (flags might affect env)
    template5, delta5 = template_env_manager.find_matching_template(
        ("python", "--solver=classic")
    )
    assert template5 is None


def test_tmp_env_with_template_cloning(
    tmp_env: TmpEnvFixture,
    template_env_manager: TemplateEnvManager | None,
) -> None:
    """Test that tmp_env can clone from template for Python-only envs."""
    if template_env_manager is None:
        pytest.skip("Template environment manager not available")

    # Create env with just Python - should clone from template
    with tmp_env("python") as prefix:
        assert PrefixData(prefix).is_environment()
        # Verify Python is installed
        python_records = [
            rec
            for rec in PrefixData(prefix).iter_records()
            if rec.name == "python"
        ]
        assert python_records, "Python package should be installed"


def test_tmp_env_clone_and_install_delta(
    tmp_env: TmpEnvFixture,
    template_env_manager: TemplateEnvManager | None,
) -> None:
    """Test that tmp_env can clone template and install delta packages."""
    if template_env_manager is None:
        pytest.skip("Template environment manager not available")

    # Create env with Python + pip - should clone Python template and install pip
    # (or clone python+pip template directly)
    with tmp_env("python", "pip") as prefix:
        assert PrefixData(prefix).is_environment()
        # Verify both Python and pip are installed
        records = {rec.name for rec in PrefixData(prefix).iter_records()}
        assert "python" in records, "Python package should be installed"
        assert "pip" in records, "pip package should be installed"
