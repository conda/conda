# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""

import sys
from collections import defaultdict
from logging import getLogger

from boltons.setutils import IndexedSet

from .base.constants import DEFAULTS_CHANNEL_NAME, UNKNOWN_CHANNEL
from .base.context import context, reset_context
from .common.constants import TRACE
from .common.io import dashlist, env_vars, time_recorder
from .common.iterators import groupby_to_dict as groupby
from .core.index import LAST_CHANNEL_URLS
from .core.link import PrefixSetup, UnlinkLinkTransaction
from .deprecations import deprecated
from .instructions import FETCH, LINK, SYMLINK_CONDA, UNLINK
from .models.channel import Channel, prioritize_channels
from .models.dist import Dist
from .models.enums import LinkType
from .models.match_spec import MatchSpec
from .models.records import PackageRecord
from .models.version import normalized_version
from .utils import human_bytes

deprecated.module("25.9", "26.3")

deprecated.constant("25.9", "26.3", "log", getLogger(__name__))
deprecated.constant("25.9", "26.3", "sys", sys, addendum="Use builtin `sys`.")
del sys
deprecated.constant(
    "25.9",
    "26.3",
    "defaultdict",
    defaultdict,
    addendum="Use builtin `collections.defaultdict`.",
)
del defaultdict
deprecated.constant(
    "25.9",
    "26.3",
    "IndexedSet",
    IndexedSet,
    addendum="Use `boltons.setutils.IndexedSet`.",
)
del IndexedSet
deprecated.constant(
    "25.9",
    "26.3",
    "DEFAULTS_CHANNEL_NAME",
    DEFAULTS_CHANNEL_NAME,
    addendum="Use `conda.base.constants.DEFAULTS_CHANNEL_NAME`.",
)
del DEFAULTS_CHANNEL_NAME
deprecated.constant(
    "25.9",
    "26.3",
    "UNKNOWN_CHANNEL",
    UNKNOWN_CHANNEL,
    addendum="Use `conda.base.constants.UNKNOWN_CHANNEL`.",
)
del UNKNOWN_CHANNEL
deprecated.constant(
    "25.9", "26.3", "context", context, addendum="Use `conda.base.context.context`."
)
del context
deprecated.constant(
    "25.9",
    "26.3",
    "reset_context",
    reset_context,
    addendum="Use `conda.base.context.reset_context`.",
)
del reset_context
deprecated.constant(
    "25.9", "26.3", "TRACE", TRACE, addendum="Use `conda.common.constants.TRACE`."
)
del TRACE
deprecated.constant(
    "25.9", "26.3", "dashlist", dashlist, addendum="Use `conda.common.io.dashlist`."
)
del dashlist
deprecated.constant(
    "25.9", "26.3", "env_vars", env_vars, addendum="Use `conda.common.io.env_vars`."
)
del env_vars
deprecated.constant(
    "25.9",
    "26.3",
    "time_recorder",
    time_recorder,
    addendum="Use `conda.common.io.time_recorder`.",
)
del time_recorder
deprecated.constant(
    "25.9",
    "26.3",
    "groupby",
    groupby,
    addendum="Use `conda.common.iterators.groupby_to_dict`.",
)
del groupby
deprecated.constant(
    "25.9",
    "26.3",
    "LAST_CHANNEL_URLS",
    LAST_CHANNEL_URLS,
    addendum="Use `conda.core.index.LAST_CHANNEL_URLS`.",
)
del LAST_CHANNEL_URLS
deprecated.constant(
    "25.9",
    "26.3",
    "PrefixSetup",
    PrefixSetup,
    addendum="Use `conda.core.link.PrefixSetup`.",
)
del PrefixSetup
deprecated.constant(
    "25.9",
    "26.3",
    "UnlinkLinkTransaction",
    UnlinkLinkTransaction,
    addendum="Use `conda.core.link.UnlinkLinkTransaction`.",
)
del UnlinkLinkTransaction
deprecated.constant(
    "25.9", "26.3", "FETCH", FETCH, addendum="Use `conda.instructions.FETCH`."
)
del FETCH
deprecated.constant(
    "25.9", "26.3", "LINK", LINK, addendum="Use `conda.instructions.LINK`."
)
del LINK
deprecated.constant(
    "25.9",
    "26.3",
    "SYMLINK_CONDA",
    SYMLINK_CONDA,
    addendum="Use `conda.instructions.SYMLINK_CONDA`.",
)
del SYMLINK_CONDA
deprecated.constant(
    "25.9", "26.3", "UNLINK", UNLINK, addendum="Use `conda.instructions.UNLINK`."
)
del UNLINK
deprecated.constant(
    "25.9", "26.3", "Channel", Channel, addendum="Use `conda.models.channel.Channel`."
)
del Channel
deprecated.constant(
    "25.9",
    "26.3",
    "prioritize_channels",
    prioritize_channels,
    addendum="Use `conda.models.channel.prioritize_channels`.",
)
del prioritize_channels
deprecated.constant(
    "25.9", "26.3", "Dist", Dist, addendum="Use `conda.models.dist.Dist`."
)
del Dist
deprecated.constant(
    "25.9", "26.3", "LinkType", LinkType, addendum="Use `conda.models.enums.LinkType`."
)
del LinkType
deprecated.constant(
    "25.9",
    "26.3",
    "MatchSpec",
    MatchSpec,
    addendum="Use `conda.models.match_spec.MatchSpec`.",
)
del MatchSpec
deprecated.constant(
    "25.9",
    "26.3",
    "PackageRecord",
    PackageRecord,
    addendum="Use `conda.models.records.PackageRecord`.",
)
del PackageRecord
deprecated.constant(
    "25.9",
    "26.3",
    "normalized_version",
    normalized_version,
    addendum="Use `conda.models.version.normalized_version`.",
)
del normalized_version
deprecated.constant(
    "25.9",
    "26.3",
    "human_bytes",
    human_bytes,
    addendum="Use `conda.utils.human_bytes`.",
)
del human_bytes
