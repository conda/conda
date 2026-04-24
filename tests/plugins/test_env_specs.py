# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import functools
from pathlib import Path
from xml.etree import ElementTree

import pytest

from conda import plugins
from conda.auxlib.ish import dals
from conda.exceptions import (
    AmbiguousEnvironmentSpecPlugin,
    EnvironmentSpecPluginNotDetected,
    EnvironmentSpecPluginSelectionError,
    PluginError,
)
from conda.models.environment import Environment, EnvironmentConfig
from conda.models.match_spec import MatchSpec
from conda.plugins import environment_specifiers
from conda.plugins.types import (
    CondaEnvironmentSpecifier,
    EnvironmentFormat,
    EnvironmentSpecBase,
)


class NaughtySpec(EnvironmentSpecBase):
    def __init__(self, source: str):
        self.source = source

    def can_handle(self):
        raise TypeError("This is a naughty spec")

    def env(self):
        raise TypeError("This is a naughty spec")


class NaughtySpecPlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="naughty",
            environment_spec=NaughtySpec,
        )


class RandomSpec(EnvironmentSpecBase):
    extensions = {".random"}

    def __init__(self, filename: str):
        self.filename = filename

    def can_handle(self):
        for ext in RandomSpec.extensions:
            if self.filename.endswith(ext):
                return True
        return False

    def env(self):
        return Environment(prefix="/somewhere", platform=["linux-64"])


@pytest.fixture()
def xml_env(tmp_path) -> Path:
    """
    XML environment definition
    """
    env_path = tmp_path / "environment.xml"
    xml = dals("""
        <?xml version="1.0" encoding="UTF-8"?>
        <Environment>
            <Channels>
                <Channel>conda-forge</Channel>
            </Channels>
            <Dependencies>
                <Conda>
                    <Dependency>python &gt;=3.10</Dependency>
                    <Dependency>numpy &gt;=1,&lt;2</Dependency>
                </Conda>
                <Pypi>
                    <Dependency>myapi</Dependency>
                </Pypi>
            </Dependencies>
        </Environment>
    """)

    env_path.write_text(xml)

    return env_path


@pytest.fixture()
def xml_env_invalid(tmp_path) -> Path:
    """
    XML environment definition
    """
    env_path = tmp_path / "environment.xml"
    xml = dals("""
    Invalid XML!!!
    """)

    env_path.write_text(xml)

    return env_path


class XmlEnvSpec(EnvironmentSpecBase):
    """
    Test Env spec that parses XML

    Example: see ``xml_env`` fixture
    """

    detection_supported = True

    def __init__(self, filename: str):
        self.filename = filename

    @functools.cached_property
    def _env(self):
        root = ElementTree.parse(self.filename).getroot()
        channels, dependencies, external = [], [], []

        if root.find("Channels") is not None:
            channels = [elm.text for elm in root.find("Channels")]
        if root.find("Dependencies") is not None:
            if root.find("Dependencies").find("Conda") is not None:
                dependencies = [
                    elm.text for elm in root.find("Dependencies").find("Conda")
                ]
            if root.find("Dependencies").find("Pypi") is not None:
                external = [elm.text for elm in root.find("Dependencies").find("Pypi")]

        return Environment(
            config=EnvironmentConfig(channels=channels),
            requested_packages=[MatchSpec(dep) for dep in dependencies],
            external_packages={"pypi": external},
            platform="linux-64",
        )

    def can_handle(self):
        return getattr(self, "env", None) is not None

    @property
    def env(self):
        return self._env


class XMLSpecPlugin:
    """
    XML environment spec parser that handles any xml file (i.e. "*.xml")
    """

    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="xml-spec",
            environment_spec=XmlEnvSpec,
            default_filenames=("*.xml",),
        )


class XMLSpecPlugin2:
    """
    XML environment spec parser, but only handles files named, "env.xml" and "environment.xml"
    """

    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="xml-spec-2",
            environment_spec=XmlEnvSpec,
            default_filenames=("env.xml", "environment.xml"),
        )


class RandomSpecNoAutoDetect(RandomSpec):
    detection_supported = False


class RandomSpecPlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="rand-spec",
            environment_spec=RandomSpec,
        )


class RandomSpecPlugin2:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="rand-spec-2",
            environment_spec=RandomSpec,
        )


class RandomSpecPluginNoAutodetect:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="rand-spec-no-autodetect",
            environment_spec=RandomSpecNoAutoDetect,
        )


class RandomSpecAliasesPlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="random",
            aliases=("rand-spec", "rnd"),
            environment_spec=RandomSpec,
        )


@pytest.fixture()
def dummy_random_spec_plugin(plugin_manager):
    random_spec_plugin = RandomSpecPlugin()
    plugin_manager.register(random_spec_plugin)

    return plugin_manager


@pytest.fixture()
def dummy_random_spec_plugin2(plugin_manager):
    random_spec_plugin = RandomSpecPlugin2()
    plugin_manager.register(random_spec_plugin)

    return plugin_manager


@pytest.fixture()
def dummy_random_spec_plugin_no_autodetect(plugin_manager):
    random_spec_plugin = RandomSpecPluginNoAutodetect()
    plugin_manager.register(random_spec_plugin)

    return plugin_manager


@pytest.fixture()
def naughty_spec_plugin(plugin_manager):
    plg = NaughtySpecPlugin()
    plugin_manager.register(plg)

    return plugin_manager


@pytest.fixture()
def plugin_manager_with_specifiers(plugin_manager):
    """Plugin manager with built-in environment specifier plugins loaded."""
    plugin_manager.load_plugins(*environment_specifiers.plugins)
    return plugin_manager


@pytest.fixture()
def plugin_manager_with_xml_spec(plugin_manager):
    xml_spec = XMLSpecPlugin()
    plugin_manager.load_plugins(xml_spec)
    return plugin_manager


@pytest.fixture()
def plugin_manager_with_xml_spec_2(plugin_manager_with_xml_spec):
    xml_spec = XMLSpecPlugin2()
    plugin_manager_with_xml_spec.load_plugins(xml_spec)

    return plugin_manager_with_xml_spec


@pytest.fixture()
def dummy_random_spec_plugin_aliases(plugin_manager):
    random_spec_plugin = RandomSpecAliasesPlugin()
    plugin_manager.register(random_spec_plugin)

    return plugin_manager


def test_dummy_random_spec_is_registered(dummy_random_spec_plugin):
    """
    Ensures that our dummy random spec has been registered and can recognize .random files
    """
    filename = "test.random"
    env_spec_backend = dummy_random_spec_plugin.get_environment_specifier(filename)
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.environment_spec(filename).env is not None

    env_spec_backend = dummy_random_spec_plugin.get_environment_specifier_by_name(
        source=filename, name="rand-spec"
    )
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.environment_spec(filename).env is not None

    env_spec_backend = dummy_random_spec_plugin.detect_environment_specifier(
        source=filename
    )
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.environment_spec(filename).env is not None


def test_raises_an_error_if_file_is_unhandleable(dummy_random_spec_plugin):
    """
    Ensures that our dummy random spec does not recognize non-".random" files
    """
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        dummy_random_spec_plugin.detect_environment_specifier("test.random-not")


def test_raises_an_error_if_plugin_name_does_not_exist(dummy_random_spec_plugin):
    """
    Ensures that an error is raised if the user requests a plugin that doesn't exist
    """
    with pytest.raises(EnvironmentSpecPluginSelectionError):
        dummy_random_spec_plugin.get_environment_specifier_by_name(
            name="uhoh", source="test.random"
        )


def test_raises_an_error_if_named_plugin_can_not_be_handled(
    dummy_random_spec_plugin,
):
    """
    Ensures that an error is raised if the user requests a plugin exists, but can't be handled
    """
    with pytest.raises(
        PluginError,
        match=r"Requested plugin 'rand-spec' is unable to handle environment spec",
    ):
        dummy_random_spec_plugin.get_environment_specifier_by_name(
            name="rand-spec", source="test.random-not-so-much"
        )


def test_raise_error_for_multiple_registered_installers(
    dummy_random_spec_plugin,
    dummy_random_spec_plugin2,
):
    """
    Ensures that we raise an error when more than one env installer is found
    for the same section.
    """
    filename = "test.random"
    with pytest.raises(
        AmbiguousEnvironmentSpecPlugin,
        match=r"File 'test\.random' can be handled by multiple formats\.",
    ) as error:
        dummy_random_spec_plugin.get_environment_specifier(filename)

    # More assertions to make sure the error message includes suggestions
    assert "Matched formats:" in str(error.value)
    assert "rand-spec" in str(error.value)
    assert "rand-spec-2" in str(error.value)


def test_raise_error_for_overlapping_default_filename(
    plugin_manager_with_xml_spec_2, xml_env
):
    """
    Ensure that we raise an error when default filenames overlap(``*.xml``)
    """
    with pytest.raises(
        AmbiguousEnvironmentSpecPlugin,
        match=r"File '(.+)environment.xml' matches the default filename pattern for multiple formats.",
    ) as error:
        plugin_manager_with_xml_spec_2.detect_environment_specifier(str(xml_env))

    # More assertions to make sure the error message includes suggestions
    assert "Matched formats:" in str(error.value)
    assert "xml-spec" in str(error.value)
    assert "xml-spec-2" in str(error.value)


def test_raises_an_error_if_no_plugins_found(dummy_random_spec_plugin_no_autodetect):
    """
    Ensures that our a plugin with autodetect disabled does not get detected
    """
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        dummy_random_spec_plugin_no_autodetect.get_environment_specifier("test.random")


def test_explicitly_select_a_non_autodetect_plugin(
    dummy_random_spec_plugin, dummy_random_spec_plugin_no_autodetect
):
    """
    Ensures that our a plugin with autodetect disabled can be explicitly selected
    """
    env_spec = dummy_random_spec_plugin.get_environment_specifier(
        "test.random", name="rand-spec-no-autodetect"
    )
    assert env_spec.name == "rand-spec-no-autodetect"
    assert env_spec.environment_spec.detection_supported is False


def test_naughty_plugin_does_not_cause_unhandled_errors(
    plugin_manager,
    dummy_random_spec_plugin,
    dummy_random_spec_plugin_no_autodetect,
    naughty_spec_plugin,
):
    """
    Ensures that explicitly selecting a plugin that has errors is handled appropriately
    """
    filename = "test.random"
    with pytest.raises(
        EnvironmentSpecPluginSelectionError,
        match=r"Could not parse 'test.random' as 'naughty'.",
    ):
        plugin_manager.get_environment_specifier_by_name(filename, "naughty")


def test_naught_plugin_does_not_cause_unhandled_errors_during_detection(
    plugin_manager,
    dummy_random_spec_plugin,
    dummy_random_spec_plugin_no_autodetect,
    naughty_spec_plugin,
):
    """
    Ensure that plugins that cause errors does not break plugin detection
    """
    filename = "test.random"
    env_spec_backend = plugin_manager.detect_environment_specifier(filename)
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.environment_spec(filename).env is not None


@pytest.mark.parametrize(
    "filename,expected_plugin",
    [
        ("requirements.txt", "requirements.txt"),
        ("spec.txt", "requirements.txt"),
        ("environment.yml", "cep-24"),  # cep-24 is registered with tryfirst=True
        ("environment.yaml", "cep-24"),
        ("explicit.txt", "explicit"),
    ],
)
def test_detect_environment_specifier_by_filename(
    plugin_manager_with_specifiers,
    tmp_path,
    filename,
    expected_plugin,
):
    """Test filename-based filtering in two-phase detection."""
    # Create a test file with appropriate content
    test_file = tmp_path / filename
    if "requirements" in filename or "spec" in filename:
        test_file.write_text("numpy==1.20.0\npandas>=1.0")
    elif "environment" in filename:
        test_file.write_text("name: test\ndependencies:\n  - python=3.8")
    elif "explicit" in filename:
        test_file.write_text(
            "@EXPLICIT\nhttps://repo.anaconda.com/pkgs/main/linux-64/python-3.8.0-0.tar.bz2"
        )

    specifier = plugin_manager_with_specifiers.detect_environment_specifier(
        str(test_file)
    )
    assert specifier.name == expected_plugin


def test_detect_environment_specifier_phase2_fallback(
    plugin_manager_with_specifiers,
    tmp_path,
):
    """Test fallback works when filename doesn't match."""
    # Create a file with non-standard name but valid requirements.txt content
    test_file = tmp_path / "my-custom-deps.txt"
    test_file.write_text("numpy==1.20.0\npandas>=1.0")

    # Should fall back to content-based detection
    specifier = plugin_manager_with_specifiers.detect_environment_specifier(
        str(test_file)
    )
    assert specifier.name == "requirements.txt"  # Detected by content


def test_detect_environment_specifier_pattern_matching_with_wildcard(
    plugin_manager_with_xml_spec, xml_env
):
    """Test that fnmatch patterns work for plugins with wildcards."""
    # Should match the wildcard pattern
    specifier = plugin_manager_with_xml_spec.detect_environment_specifier(str(xml_env))
    assert specifier.name == "xml-spec"

    env = specifier.environment_spec(str(xml_env)).env

    assert env.name is None
    assert env.requested_packages == [
        MatchSpec("python>=3.10"),
        MatchSpec("numpy>=1,<2"),
    ]
    assert env.external_packages == {"pypi": ["myapi"]}


def test_detect_environment_specifier_with_invalid_contents(
    plugin_manager_with_xml_spec, xml_env_invalid
):
    """
    Test when filename matches but the content is invalid.
    """
    with pytest.raises(PluginError) as error:
        plugin_manager_with_xml_spec.detect_environment_specifier(str(xml_env_invalid))

    assert (
        "PluginError: Failed to parse environment specification from file: syntax error"
        in str(error)
    )


def test_detect_environment_specifier_no_match_raises_error(
    plugin_manager_with_specifiers,
    tmp_path,
):
    """Test that unrecognized files raise appropriate error."""
    # Create a file that doesn't match any plugin
    test_file = tmp_path / "unknown.xyz"
    test_file.write_text("some!!!@#()random!@#!)@#!@#)@!#cont@#!#!@#!@ent")

    # Should raise error when no plugin can handle it
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        plugin_manager_with_specifiers.detect_environment_specifier(str(test_file))


def test_get_spec_by_aliases(plugin_manager, dummy_random_spec_plugin_aliases):
    """
    Ensures that our dummy random spec has been registered and can be recognized by its aliases
    """
    filename = "test.random"
    env_spec_backend = plugin_manager.get_environment_specifier_by_name(
        filename, "rand-spec"
    )
    assert env_spec_backend.name == "random"
    assert env_spec_backend.environment_spec(filename).env is not None

    env_spec_backend = plugin_manager.get_environment_specifier_by_name(filename, "rnd")
    assert env_spec_backend.name == "random"
    assert env_spec_backend.environment_spec(filename).env is not None

    # Ensure an error is raised for an alias that doesn't exist
    with pytest.raises(EnvironmentSpecPluginSelectionError):
        env_spec_backend = plugin_manager.get_environment_specifier_by_name(
            filename, "notalias"
        )


def test_detect_spec_with_aliases(plugin_manager, dummy_random_spec_plugin_aliases):
    """
    Ensures that our dummy random spec can detect valid inputs
    """
    filename = "test.random"
    env_spec_backend = plugin_manager.detect_environment_specifier("test.random")
    assert env_spec_backend.name == "random"
    assert env_spec_backend.environment_spec(filename).env is not None


def test_alias_normalization():
    """Test that aliases are normalized."""
    # Test alias normalization (mixed case, whitespace, and duplicates)
    exporter = CondaEnvironmentSpecifier(
        name="random",
        aliases=("rnd", "RND", "   range"),
        environment_spec=RandomSpec,
    )

    # Aliases should be normalized to lowercase and stripped
    assert exporter.aliases == (
        "rnd",
        "range",
    )

    # Test invalid alias type raises error
    with pytest.raises(PluginError, match="Invalid plugin aliases"):
        CondaEnvironmentSpecifier(
            name="bad-aliases-type",
            aliases=(123, "valid"),  # Non-string alias
            environment_spec=RandomSpec,
        )


def test_alias_and_name_collision_detect(
    plugin_manager, dummy_random_spec_plugin_aliases, dummy_random_spec_plugin
):
    """
    Test that name/alias collision detection works for all the different ways
    environment spec plugins can be requested from the plugin manager.
    """
    with pytest.raises(PluginError):
        plugin_manager.get_environment_specifiers()

    with pytest.raises(PluginError):
        plugin_manager.get_environment_specifier_by_name("something.random", "random")

    with pytest.raises(
        PluginError,
        match=r"'something\.random' can be handled by multiple formats\.",
    ):
        plugin_manager.detect_environment_specifier("something.random")


@pytest.mark.parametrize(
    "spec_name,expected_description,expected_environment_format",
    [
        (
            "environment.yml",
            "Standard YAML environment specification with dependencies",
            EnvironmentFormat.environment,
        ),
        (
            "explicit",
            "Explicit package URLs for fully reproducible environments",
            EnvironmentFormat.lockfile,
        ),
        (
            "requirements.txt",
            "Simple text file with package specifications",
            EnvironmentFormat.environment,
        ),
        (
            "cep-24",
            "CEP-24 compliant YAML environment specification",
            EnvironmentFormat.environment,
        ),
    ],
)
def test_builtin_specifiers_have_metadata(
    plugin_manager_with_specifiers,
    spec_name: str,
    expected_description: str,
    expected_environment_format: bool,
):
    """Test that all built-in specifiers have meaningful descriptions and correct lockfile classification."""
    # Get all environment specifiers (returns a dict)
    specifiers = plugin_manager_with_specifiers.get_environment_specifiers()

    # Get the specifier by name (it's the key in the dict)
    specifier = specifiers.get(spec_name)

    assert specifier is not None, f"Specifier {spec_name} not found"

    # Verify description is meaningful (not just the name)
    assert specifier.description is not None
    assert specifier.description == expected_description
    assert (
        specifier.description != spec_name
    )  # Should be more descriptive than just the name

    # Verify lockfile classification
    assert specifier.environment_format == expected_environment_format


class SinglePlatformSpec(EnvironmentSpecBase):
    """Exercises default `env_for` / `available_platforms` implementations."""

    def can_handle(self) -> bool:
        return True

    @property
    def env(self) -> Environment:
        from conda.base.context import context

        return Environment(prefix="/somewhere", platform=context.subdir)


class MultiPlatformSpec(EnvironmentSpecBase):
    """Overrides `available_platforms` + `env_for` to expose multiple platforms."""

    _PLATFORMS = ("linux-64", "osx-arm64", "win-64")

    def can_handle(self) -> bool:
        return True

    @property
    def env(self) -> Environment:
        return Environment(prefix="/somewhere", platform=self._PLATFORMS[0])

    @property
    def available_platforms(self):
        return self._PLATFORMS

    def env_for(self, platform: str) -> Environment:
        if platform not in self._PLATFORMS:
            raise ValueError(f"Platform {platform!r} not available")
        return Environment(prefix="/somewhere", platform=platform)


@pytest.fixture(
    params=[
        pytest.param(SinglePlatformSpec, id="default-single-platform"),
        pytest.param(MultiPlatformSpec, id="override-multi-platform"),
    ]
)
def spec_and_platforms(request):
    from conda.base.context import context

    expected = {
        SinglePlatformSpec: (context.subdir,),
        MultiPlatformSpec: ("linux-64", "osx-arm64", "win-64"),
    }[request.param]
    return request.param(), expected


def test_available_platforms(spec_and_platforms):
    """`available_platforms` returns every platform the spec covers."""
    spec, expected = spec_and_platforms
    assert spec.available_platforms == expected


def test_env_for_returns_requested_platform(spec_and_platforms):
    """`env_for(platform)` returns an `Environment` for the requested platform."""
    spec, expected = spec_and_platforms
    for platform in expected:
        assert spec.env_for(platform).platform == platform


def test_env_for_unknown_platform_raises(spec_and_platforms):
    """`env_for` raises for platforms outside `available_platforms`."""
    spec, _ = spec_and_platforms
    with pytest.raises(ValueError, match="not available"):
        spec.env_for("not-a-real-platform")


def test_env_spec_iteration_pattern(spec_and_platforms):
    """Standard iteration pattern: `env_for` over `available_platforms`."""
    spec, expected = spec_and_platforms
    envs = [spec.env_for(p) for p in spec.available_platforms]
    assert tuple(e.platform for e in envs) == expected


class DescribeSpecifierLockfilePlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="my-lock-v1",
            aliases=("mylock",),
            default_filenames=("my.lock",),
            environment_spec=RandomSpec,
            environment_format=EnvironmentFormat.lockfile,
        )


def test_describe_specifier_formats_groups_by_category(
    plugin_manager_with_specifiers,
):
    """Specifiers are grouped by category."""
    specifiers = list(
        plugin_manager_with_specifiers.get_hook_results("environment_specifiers")
    )
    rendered = plugin_manager_with_specifiers.describe_formats(specifiers)
    assert "Environment specs:" in rendered
    if "Lockfiles:" in rendered:
        assert rendered.index("Environment specs:") < rendered.index("Lockfiles:")


def test_describe_specifier_formats_includes_registered_lockfile_plugin(
    plugin_manager_with_specifiers,
    request: pytest.FixtureRequest,
):
    """A lockfile specifier plugin appears under the Lockfiles section."""
    plugin = DescribeSpecifierLockfilePlugin()
    plugin_manager_with_specifiers.register(plugin)
    request.addfinalizer(lambda: plugin_manager_with_specifiers.unregister(plugin))

    specifiers = list(
        plugin_manager_with_specifiers.get_hook_results("environment_specifiers")
    )
    rendered = plugin_manager_with_specifiers.describe_formats(specifiers)
    assert "Lockfiles:" in rendered
    assert "- my-lock-v1 (mylock)" in rendered


def test_describe_specifier_formats_empty(plugin_manager):
    """Without registered specifiers the description is empty."""
    assert plugin_manager.describe_formats([]) == ""
