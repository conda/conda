#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""
Synchronize local patch files with repodata.fly.dev
"""

import logging
import os
from pathlib import Path
from typing import NamedTuple, cast, Iterator

from requests import Response

from . import truncateable
from .repodata_proxy import RepodataUrl

log = logging.getLogger(__name__)


def line_offsets(path: Path) -> int:
    """
    Return byte offset to next-to-last line in path.
    """
    sum_val = 0
    offsets = []
    with path.open("rb") as data:
        for line in cast(Iterator, data):
            offsets.append(sum_val)
            sum_val += len(line)
    try:
        return offsets[-2]
    except IndexError:
        return 0


class SyncJlap(NamedTuple):
    repodata_url: RepodataUrl

    def get_request_headers(self) -> dict:
        cache_key = self.repodata_url.get_cache_repodata_jlap_key()

        if not cache_key.exists():
            cache_key.parent.mkdir(parents=True, exist_ok=True)
            headers = {"Cache-Control": "no-cache"}
        else:
            offset = line_offsets(cache_key)
            headers = {"Range": "bytes=%d-" % offset}

        return headers

    def get_offset(self) -> int:
        cache_key = self.repodata_url.get_cache_repodata_jlap_key()

        if not cache_key.exists():
            return 0
        else:
            return line_offsets(cache_key)

    def save_response_to_jlap_cache(self, response: Response) -> Path:
        """
        If we receive a successful response (200 or 206) we write this to
        the cache location specify by our RepodataUrl object.
        """
        cache_key = self.repodata_url.get_cache_repodata_jlap_key()
        offset = self.get_offset()

        if response.status_code == 200:
            log.info("Full download")
            cache_key.write_bytes(response.content)
        elif response.status_code == 206:
            size_before = os.stat(cache_key).st_size
            os.truncate(cache_key, offset)
            with cache_key.open("ba") as out:
                tell = out.tell()
                log.info(
                    "Append %d-%d (%d lines)",
                    tell,
                    tell + len(response.content),
                    len(response.content.splitlines()),
                )
                out.write(response.content)
            size_after = os.stat(cache_key).st_size
            log.info(
                "Was %d, now %d bytes, delta %d",
                size_before,
                size_after,
                (size_after - size_before),
            )
        else:
            log.info("Unexpected status %d", response.status_code)

        # verify checksum
        # can cache checksum of next-to-last line instead of recalculating all
        # (remove consumed lines from local file and store full length)
        with cache_key.open("rb") as fp:
            jlap = truncateable.JlapReader(fp)
            for _obj in jlap.read_objs():
                pass

        return cache_key
