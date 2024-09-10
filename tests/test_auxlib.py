# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from enum import Enum
from typing import TYPE_CHECKING

import pytest
from frozendict import deepfreeze

from conda.auxlib import collection, ish
from conda.base.constants import UpdateModifier

if TYPE_CHECKING:
    from typing import Any, ModuleType


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
    assert collection.make_immutable(unfrozen) == deepfreeze(
        unfrozen, {Enum: lambda x: x}
    )


@pytest.mark.parametrize(
    "module,function,raises",
    [
        (collection, "AttrDict", None),
        (ish, "_get_attr", TypeError),
        (ish, "find_or_none", TypeError),
        (ish, "find_or_raise", TypeError),
    ],
)
def test_deprecations(
    module: ModuleType, function: str, raises: type[Exception] | None
) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(module, function)()
