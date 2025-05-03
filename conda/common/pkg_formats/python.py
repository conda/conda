# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Common Python package format utilities."""

from ...deprecations import deprecated
from ...plugins.prefix_data_loaders.pypi.pkg_format import (  # noqa
    AND,
    COMPARE_OP,
    DEFAULT_MARKER_CONTEXT,
    IDENTIFIER,
    MARKER_OP,
    NON_SPACE,
    OR,
    PARTIAL_PYPI_SPEC_PATTERN,
    PY_FILE_RE,
    PYPI_CONDA_DEPS,
    PYPI_TO_CONDA,
    STRING_CHUNK,
    VERSION_IDENTIFIER,
    Evaluator,
    MetadataWarning,
    PySpec,
    PythonDistribution,
    PythonDistributionMetadata,
    PythonEggInfoDistribution,
    PythonEggLinkDistribution,
    PythonInstalledDistribution,
    _is_literal,
    evaluator,
    get_default_marker_context,
    get_dist_file_from_egg_link,
    get_site_packages_anchor_files,
    interpret,
    norm_package_name,
    norm_package_version,
    parse_marker,
    parse_specification,
    pypi_name_to_conda_name,
    split_spec,
)

deprecated.module(
    "25.9",
    "26.3",
    addendum="Use 'conda.plugins.prefix_data_loaders.pypi.pkg_format' hook instead",
)
