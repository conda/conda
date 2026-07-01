# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Optional py-rattler fast path for PrefixGraph construction.

Scope: this module is imported lazily from
``conda.models.prefix_graph.PrefixGraph.__init__``. If py-rattler is
not installed, ``try_build_graph`` returns ``None`` and the caller
falls back to the pure-Python name-indexed path from #15971.

Strategy:

1. Convert the conda ``PrefixRecord`` inputs to ``rattler.PackageRecord``
   once per call, caching the view on the conda record so repeat
   PrefixGraph calls within one process skip the reconversion.
2. Build adjacency using ``rattler.MatchSpec`` for dep parsing and
   ``rattler.PackageRecord.matches`` for the match test. Both are
   Rust-backed; parse is ~4x faster, match is ~5x faster than conda's
   native implementations (measured in S18).
3. Cache parsed ``rattler.MatchSpec`` by dep string within a single
   call: real prefixes have significant dep-string repetition.
4. Return the unsorted conda-shaped adjacency dict and let
   ``PrefixGraph._toposort()`` keep conda's stable ordering and
   special-case edge handling.
5. Spec matching (the ``specs`` argument of PrefixGraph) uses conda's
   ``MatchSpec`` because callers hand us conda ``MatchSpec`` instances
   built from sources we don't control, which may use conda grammar
   rattler rejects.

Returns ``(graph, spec_matches)`` in the same shape the pure-Python
loop produces. Returns ``None`` for any error so conda's fallback
keeps operating correctly; the fast path is strictly additive.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import rattler as _rattler
except ImportError:
    _rattler = None

if TYPE_CHECKING:
    from typing import Any

    from .match_spec import MatchSpec
    from .records import PrefixRecord

_RATTLER_VIEW_ATTR = "_conda_prefix_graph_rattler_view"


def is_available() -> bool:
    return _rattler is not None


def _to_rattler_record(rec) -> Any | None:
    cached = getattr(rec, _RATTLER_VIEW_ATTR, None)
    if cached is not None:
        return cached
    try:
        cached = _rattler.PackageRecord(
            name=rec.name,
            version=str(rec.version),
            build=rec.build or "",
            build_number=rec.build_number or 0,
            subdir=rec.subdir,
            noarch=_noarch_value(rec),
            depends=list(rec.depends or ()),
        )
    except (ValueError, RuntimeError, TypeError, AttributeError):
        return None
    try:
        setattr(rec, _RATTLER_VIEW_ATTR, cached)
    except (AttributeError, TypeError):
        pass
    return cached


def _noarch_value(rec) -> str | None:
    noarch = getattr(rec, "noarch", None)
    if noarch is None:
        if getattr(rec, "subdir", None) == "noarch":
            return "generic"
        return None
    s = str(noarch).lower()
    if s in ("python", "generic"):
        return s
    if s == "true":
        return "generic"
    return None


def try_build_graph(
    records: tuple[PrefixRecord, ...],
    specs: set[MatchSpec],
) -> tuple[dict, dict] | None:
    """Attempt the rattler-backed build. Returns (graph, spec_matches)
    or ``None`` if the caller should use the pure-Python fallback.
    """
    if _rattler is None or not records:
        return None

    # Pre-convert every record. Abort to the fallback if any conversion
    # fails so we don't produce a partial result.
    rec_to_rattler: dict[int, Any] = {}
    for rec in records:
        rrec = _to_rattler_record(rec)
        if rrec is None:
            return None
        rec_to_rattler[id(rec)] = rrec

    by_name: dict[str, list[Any]] = {}
    for rec in records:
        by_name.setdefault(rec.name, []).append(rec)

    spec_cache: dict[str, Any] = {}

    def _rattler_spec(dep: str):
        cached = spec_cache.get(dep)
        if cached is not None:
            return cached
        try:
            parsed = _rattler.MatchSpec(dep)
        except (ValueError, RuntimeError, TypeError):
            parsed = False
        spec_cache[dep] = parsed
        return parsed

    graph: dict[Any, dict[Any, None]] = {}
    unsorted_spec_matches: dict[Any, dict[Any, None]] = {}

    for node in records:
        parent_nodes: dict[Any, None] = {}
        for dep in node.depends:
            spec = _rattler_spec(dep)
            if spec is False:
                return None
            name = _matchspec_name(spec)
            candidates = by_name.get(name, ())
            for candidate in candidates:
                cand_rrec = rec_to_rattler[id(candidate)]
                try:
                    if spec.matches(cand_rrec):
                        parent_nodes[candidate] = None
                except (ValueError, RuntimeError, TypeError):
                    return None
        graph[node] = parent_nodes

        if specs:
            matching = {s: None for s in specs if s.match(node)}
            if matching:
                unsorted_spec_matches[node] = matching

    return graph, unsorted_spec_matches


def _matchspec_name(spec) -> str:
    """Extract the plain package name from a rattler.MatchSpec."""
    name_obj = spec.name
    source = getattr(name_obj, "source", None)
    if isinstance(source, str):
        return source
    return str(name_obj).split('"', 2)[1] if '"' in str(name_obj) else str(name_obj)
