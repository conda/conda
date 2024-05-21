"""
Base class for conda env spec plugins
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..env import Environment


class BaseEnvSpec:
    msg: str | None = None

    def can_handle(self) -> bool:
        raise NotImplementedError

    @property
    def environment(self) -> Environment:
        raise NotImplementedError
