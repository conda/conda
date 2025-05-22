# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest

from conda.exceptions import CondaValueError
from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec


def test_create_environment_no_prefix():
    with pytest.raises(CondaValueError):
        Environment(platform="platform", prefix=None)


def test_environments_merge():
    env1 = Environment(
        prefix="/path/to/env1",
        platform="one",
        config={"primitive_one": "yes", "list_one": [1, 2, 4]},
        external_packages={"pip": ["one", "two"], "other": ["three"]},
        explicit_specs=[MatchSpec("somepackage.conda")],
        requested_specs=[MatchSpec("numpy"), MatchSpec("pandas")],
        variables={"PATH": "/usr/bin"},
    )
    env2 = Environment(
        prefix="/path/to/env1",
        platform="one",
        config={"primitive_one": "no", "primitive_two": "yes", "list_one": [3]},
        external_packages={"pip": ["two", "flask"], "a": ["nother"]},
        explicit_specs=[MatchSpec("somepackageother.conda")],
        requested_specs=[MatchSpec("numpy"), MatchSpec("flask")],
        variables={"VAR": "IABLE"},
    )
    merged = Environment.merge(env1, env2)
    assert merged.prefix == "/path/to/env1"
    assert merged.platform == "one"
    assert merged.config == {
        "primitive_one": "no",
        "primitive_two": "yes",
        "list_one": [1, 2, 4, 3],
    }
    assert merged.external_packages == {
        "pip": ["one", "two", "flask"],
        "other": ["three"],
        "a": ["nother"],
    }
    assert set(merged.requested_specs) == set(
        [MatchSpec("pandas"), MatchSpec("flask"), MatchSpec("numpy")]
    )
    assert set(merged.explicit_specs) == set(
        [MatchSpec("somepackageother.conda"), MatchSpec("somepackage.conda")]
    )
    assert merged.variables == {"PATH": "/usr/bin", "VAR": "IABLE"}


def test_environments_merge_colliding_platform():
    env1 = Environment(prefix="/path/to/env1", platform="one")
    env2 = Environment(prefix="/path/to/env2", platform="two")

    with pytest.raises(CondaValueError):
        Environment.merge(env1, env2)
