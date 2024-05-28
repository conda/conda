# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

import pytest
from frozendict import deepfreeze

from conda.auxlib.collection import make_immutable
from conda.base.constants import UpdateModifier

if TYPE_CHECKING:
    from typing import Any


IMMUTABLE = (
    "text",
    42,
    42.0,
    True,
    UpdateModifier.FREEZE_INSTALLED,
    (1, 1, 2),
    frozenset({1, 1, 2}),
)
MUTABLE = ([1, 1, 2], {1, 1, 2}, {1: 1, 2: 2})


@pytest.mark.parametrize(
    "unfrozen",
    [
        *IMMUTABLE,
        *MUTABLE,
        # make_immutable leaves a tuple as is, deepfreeze does a better job
        # (*IMMUTABLE, *MUTABLE),
        [*IMMUTABLE, *MUTABLE],
        {*IMMUTABLE},
        frozenset({*IMMUTABLE}),
        dict(enumerate((*IMMUTABLE, *MUTABLE))),
    ],
)
def test_deepfreeze(unfrozen: Any) -> None:
    assert make_immutable(unfrozen) == deepfreeze(unfrozen, {Enum: lambda x: x})
