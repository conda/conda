# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for managing the packages installed within an environment."""

from __future__ import annotations

import re
import sys
import traceback
from logging import getLogger
from os.path import basename
from pathlib import Path
from typing import TYPE_CHECKING

from ...auxlib.exceptions import ValidationError
from ...common.path import (
    get_python_site_packages_short_path,
    win_path_ok,
)
from ...common.pkg_formats.python import get_site_packages_anchor_files
from ...gateways.disk.delete import rm_rf
from ...gateways.disk.read import read_python_record
from ...models.prefix_graph import PrefixGraph

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable

    from ...models.records import PrefixRecord

log = getLogger(__name__)


def get_python_pkg_record(records: Iterable[PrefixRecord]) -> PrefixRecord | None:
    """Return the prefix record for the package python."""
    return next(
        (
            prefix_record
            for prefix_record in records
            if prefix_record.name == "python"
        ),
        None,
    )

def load_site_packages(prefix: os.PathLike, records: dict[str, PrefixRecord]) -> dict[str, PrefixRecord]:
    """
    Load non-conda-installed python packages in the site-packages of the prefix.

    Python packages not handled by conda are installed via other means,
    like using pip or using python setup.py develop for local development.

    Packages found that are not handled by conda are converted into a
    prefix record and handled in memory.

    Packages clobbering conda packages (i.e. the conda-meta record) are
    removed from the in memory representation.
    """
    python_pkg_record = get_python_pkg_record(records)
    prefix_path = Path(prefix)

    if not python_pkg_record:
        return {}

    site_packages_dir = get_python_site_packages_short_path(
        python_pkg_record.version
    )
    site_packages_path = prefix_path / win_path_ok(site_packages_dir)

    if not site_packages_path.is_dir():
        return {}

    # Get anchor files for corresponding conda (handled) python packages
    prefix_graph = PrefixGraph(records.values())
    python_records = prefix_graph.all_descendants(python_pkg_record)
    conda_python_packages = get_conda_anchor_files_and_records(
        site_packages_dir, python_records
    )

    # Get all anchor files and compare against conda anchor files to find clobbered conda
    # packages and python packages installed via other means (not handled by conda)
    sp_anchor_files = get_site_packages_anchor_files(
        site_packages_path, site_packages_dir
    )
    conda_anchor_files = set(conda_python_packages)
    clobbered_conda_anchor_files = conda_anchor_files - sp_anchor_files
    non_conda_anchor_files = sp_anchor_files - conda_anchor_files

    # If there's a mismatch for anchor files between what conda expects for a package
    # based on conda-meta, and for what is actually in site-packages, then we'll delete
    # the in-memory record for the conda package.  In the future, we should consider
    # also deleting the record on disk in the conda-meta/ directory.
    for conda_anchor_file in clobbered_conda_anchor_files:
        prefix_rec = records.pop(
            conda_python_packages[conda_anchor_file].name
        )
        try:
            extracted_package_dir = basename(prefix_rec.extracted_package_dir)
        except AttributeError:
            extracted_package_dir = "-".join(
                (prefix_rec.name, prefix_rec.version, prefix_rec.build)
            )
        prefix_rec_json_path = (
            prefix_path / "conda-meta" / f"{extracted_package_dir}.json"
        )
        try:
            rm_rf(prefix_rec_json_path)
        except OSError:
            log.debug(
                "stale information, but couldn't remove: %s", prefix_rec_json_path
            )
        else:
            log.debug("removed due to stale information: %s", prefix_rec_json_path)

    # Create prefix records for python packages not handled by conda
    new_packages = {}
    for af in non_conda_anchor_files:
        try:
            python_record = read_python_record(
                prefix_path, af, python_pkg_record.version
            )
        except OSError as e:
            log.info(
                "Python record ignored for anchor path '%s'\n  due to %s", af, e
            )
            continue
        except ValidationError:

            exc_type, exc_value, exc_traceback = sys.exc_info()

            tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
            log.warning(
                "Problem reading non-conda package record at %s. Please verify that you "
                "still need this, and if so, that this is still installed correctly. "
                "Reinstalling this package may help.",
                af,
            )
            log.debug("ValidationError: \n%s\n", "\n".join(tb))
            continue
        if not python_record:
            continue
        records[python_record.name] = python_record
        new_packages[python_record.name] = python_record

    return new_packages


def get_conda_anchor_files_and_records(site_packages_short_path, python_records):
    """Return the anchor files for the conda records of python packages."""
    anchor_file_endings = (".egg-info/PKG-INFO", ".dist-info/RECORD", ".egg-info")
    conda_python_packages = {}

    matcher = re.compile(
        r"^{}/[^/]+(?:{})$".format(
            re.escape(site_packages_short_path),
            r"|".join(re.escape(fn) for fn in anchor_file_endings),
        )
    ).match

    for prefix_record in python_records:
        anchor_paths = tuple(fpath for fpath in prefix_record.files if matcher(fpath))
        if len(anchor_paths) > 1:
            anchor_path = sorted(anchor_paths, key=len)[0]
            log.info(
                "Package %s has multiple python anchor files.\n  Using %s",
                prefix_record.record_id(),
                anchor_path,
            )
            conda_python_packages[anchor_path] = prefix_record
        elif anchor_paths:
            conda_python_packages[anchor_paths[0]] = prefix_record

    return conda_python_packages
