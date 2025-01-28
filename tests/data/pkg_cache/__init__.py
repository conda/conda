# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from importlib.resources import files

from conda.core.package_cache_data import PackageCacheRecord


def load_data_file(filename):
    with open(files().joinpath(filename)) as ifh:
        data = json.load(ifh)
    return data


def load_cache_entries(filename):
    data = load_data_file(filename)
    entries = tuple(PackageCacheRecord.from_objects(entry) for entry in data)
    return entries
