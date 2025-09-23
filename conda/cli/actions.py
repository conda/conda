# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Collection of custom argparse actions.
"""

from __future__ import annotations

from argparse import Action, _AppendAction, _CountAction, _StoreAction
from typing import TYPE_CHECKING

from ..auxlib.type_coercion import maybecall
from ..common.constants import NULL

if TYPE_CHECKING:
    from typing import Any


class NullCountAction(_CountAction):
    @staticmethod
    def _ensure_value(namespace, name, value):
        if getattr(namespace, name, NULL) in (NULL, None):
            setattr(namespace, name, value)
        return getattr(namespace, name)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = self._ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


class ExtendConstAction(Action):
    """
    A derivative of _AppendConstAction and Python 3.8's _ExtendAction
    """

    def __init__(
        self,
        option_strings,
        dest,
        const,
        default=None,
        type=None,
        choices=None,
        required=False,
        help=None,
        metavar=None,
    ):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs="*",
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        items = [] if items is None else items[:]
        items.extend(values or [self.const])
        setattr(namespace, self.dest, items)


class LazyMixin:
    _cache_: dict[str, Any]

    def __getattribute__(self, name: str) -> Any:
        # check if name is a field (i.e., already in __dict__)
        fields = super().__getattribute__("__dict__")
        if name not in fields:
            return super().__getattribute__(name)

        # create cache if it doesn't exist
        try:
            cache = super().__getattribute__("_cache_")
        except AttributeError:
            cache = self._cache_ = {}

        # populate cache if value doesn't exist
        if name not in cache:
            cache[name] = maybecall(super().__getattribute__(name))

        # return cached value
        return cache[name]


LazyAppendAction = type("LazyAppendAction", (LazyMixin, _AppendAction), {})
LazyStoreAction = type("LazyStoreAction", (LazyMixin, _StoreAction), {})
