# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from conda.testing.integration import SPACER_CHARACTER

if TYPE_CHECKING:
    from collections.abc import Iterator

    from conda.testing.fixtures import PathFactoryFixture


@pytest.fixture
def shell_wrapper_integration(
    path_factory: PathFactoryFixture,
) -> Iterator[tuple[str, str, str]]:
    prefix = path_factory(
        prefix=uuid4().hex[:4], name=SPACER_CHARACTER, suffix=uuid4().hex[:4]
    )
    history = prefix / "conda-meta" / "history"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.touch()

    prefix2 = prefix / "envs" / "charizard"
    history2 = prefix2 / "conda-meta" / "history"
    history2.parent.mkdir(parents=True, exist_ok=True)
    history2.touch()

    prefix3 = prefix / "envs" / "venusaur"
    history3 = prefix3 / "conda-meta" / "history"
    history3.parent.mkdir(parents=True, exist_ok=True)
    history3.touch()

    yield str(prefix), str(prefix2), str(prefix3)
