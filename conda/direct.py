# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Installing into environments from direct (URL based) specifications"""

from typing import Any

from .base.context import context
from .core.link import PrefixSetup, UnlinkLinkTransaction
from .core.package_cache_data import PackageCacheData, ProgressiveFetchExtract
from .core.prefix_data import PrefixData
from .exceptions import (
    CondaExitZero,
    DryRunExit,
)
from .models.match_spec import MatchSpec
from .models.records import PackageCacheRecord

DirectPackageURL = str
DirectPackageMetadata = dict[str, Any]
DirectPackages = dict[DirectPackageURL, DirectPackageMetadata]


def _matchspec_from_url_and_metadata(
    url: DirectPackageMetadata, metadata: DirectPackageMetadata
):
    checksums = {}
    for checksum_name in ["md5", "sha256"]:
        if checksum_name in metadata:
            checksums[checksum_name] = metadata[checksum_name]
    return MatchSpec(url, **checksums)


# TODO refactor conda.misc.explicit to call this function
def direct(direct_pkgs: DirectPackages, prefix: str) -> None:
    fetch_specs = [
        _matchspec_from_url_and_metadata(url, metadata)
        for url, metadata in direct_pkgs.items()
    ]

    if context.dry_run:
        raise DryRunExit()

    pfe = ProgressiveFetchExtract(fetch_specs)
    pfe.execute()

    if context.download_only:
        raise CondaExitZero(
            "Package caches prepared. "
            "UnlinkLinkTransaction cancelled with --download-only option."
        )

    # now make an UnlinkLinkTransaction with the PackageCacheRecords as inputs
    # need to add package name to fetch_specs so that history parsing keeps track of them correctly
    specs_pcrecs: list[list[MatchSpec, PackageCacheRecord]] = []
    for fetch_spec in fetch_specs:
        cache_pcrec = next(PackageCacheData.query_all(fetch_spec), None)
        if cache_pcrec is None:
            specs_pcrecs.append([fetch_spec, None])
        else:
            url = fetch_spec.get("url")
            overrides = direct_pkgs.get(url, {})
            pcrec = PackageCacheRecord.from_objects(
                cache_pcrec,
                **overrides,
            )
            spec_with_name = MatchSpec(fetch_spec, name=pcrec.name)
            specs_pcrecs.append([spec_with_name, pcrec])

    # Assert that every spec has a PackageCacheRecord
    specs_with_missing_pcrecs = [
        str(spec) for spec, pcrec in specs_pcrecs if pcrec is None
    ]
    if specs_with_missing_pcrecs:
        if len(specs_with_missing_pcrecs) == len(specs_pcrecs):
            raise AssertionError("No package cache records found")
        else:
            missing_precs_list = ", ".join(specs_with_missing_pcrecs)
            raise AssertionError(
                f"Missing package cache records for: {missing_precs_list}"
            )

    precs_to_remove = []
    prefix_data = PrefixData(prefix)
    for q, (spec, pcrec) in enumerate(specs_pcrecs):
        prec = prefix_data.get(pcrec.name, None)
        if prec:
            # If we've already got matching specifications, then don't bother re-linking it
            if next(prefix_data.query(spec), None):
                specs_pcrecs[q][0] = None
            else:
                precs_to_remove.append(prec)

    stp = PrefixSetup(
        prefix,
        precs_to_remove,
        tuple(sp[1] for sp in specs_pcrecs if sp[0]),
        (),
        tuple(sp[0] for sp in specs_pcrecs if sp[0]),
        (),
    )

    txn = UnlinkLinkTransaction(stp)
    if not context.json and not context.quiet:
        txn.print_transaction_summary()
    txn.execute()
