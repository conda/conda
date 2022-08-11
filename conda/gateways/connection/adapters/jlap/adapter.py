# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""
Cached repodata with `.jlap` incremental diffs, implemented as a ConnectionAdapter.
"""

import gzip
import json
import logging

from requests import PreparedRequest, Response
from requests.adapters import HTTPAdapter

from conda.base import constants as consts
from .repodata_proxy import RepodataUrl, fetch_repodata_json, static_file_headers, patch_files
from .sync_jlap import SyncJlap

log = logging.getLogger(__name__)


class JlapAdapter(HTTPAdapter):
    def __init__(self, base_adapter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_adapter = base_adapter

    def send(self, request, **kwargs):
        """
        Overrides the default HTTPAdapter. When this particular HTTPAdapter is in
        use, we only care about intercepting URLs that end with
        ``conda.base.constants.REPODATA_FN``
        """
        if request.url.endswith(consts.REPODATA_FN):
            log.debug("Intercept %s", request.url)

            # Pre-processing to the request, including changing its URL
            repodata_url = RepodataUrl(request.url)
            sync = SyncJlap(repodata_url)
            new_request = self.prepare_request(request, sync)
            response = self.send(new_request)

            # This means there was an error with the response. We return it immediately.
            if response.status_code > 300:
                return response

            # This step does some saving to the filesystem plus other processing
            response = self.post_response_processing(response, sync)

            # Post-processing to the response, including changing back its URL
            return self.prepare_response(response, request)
        else:
            log.debug("Skip intercept %s", request.url)
            return self.base_adapter.send(request, **kwargs)

    @staticmethod
    def prepare_request(request: PreparedRequest, sync: SyncJlap) -> PreparedRequest:
        """
        We need to specially prepare the request because it's actually being diverted
        to a different location.
        """
        new_headers = sync.get_request_headers()
        request.url = sync.repodata_url.translate_to_jlap_url()
        request.headers.update(new_headers)

        return request

    @staticmethod
    def prepare_response(response: Response, request: PreparedRequest) -> Response:
        """
        We do this to make it look like the client is getting back the original thing they
        requested and not what we actually retrieved (i.e. the JLAP stuff)
        """
        response.request = request
        response.url = request.url

        return response

    @staticmethod
    def post_response_processing(response: Response, sync: SyncJlap) -> Response:
        """
        This runs a series of actions after a successful response
        """
        json_cache = sync.repodata_url.get_cache_repodata_gzip_key()
        jlap_path = sync.save_response_to_jlap_cache(response)

        if not json_cache.exists():
            log.debug("Fetch complete %s", response.request.url)
            cache_path, digest = fetch_repodata_json(json_cache, response.request.url)
            assert digest  # check exists in patch file...

        # headers based on last modified of patch file
        file_response = static_file_headers(
            str(jlap_path.relative_to(consts.CACHE_DIR)), root=consts.CACHE_DIR
        )
        del file_response.headers["Content-Length"]

        if file_response.status_code != 200:  # file not found?
            response.status_code = file_response.status_code
            response.body = file_response.body
            response.headers = file_response.headers

            return response

        log.debug("Serve from %s", json_cache)

        new_data = patch_files(json_cache, jlap_path)
        buf = json.dumps(new_data).encode("utf-8")

        # TODO if cache is ok, read from here, skip patch, re-serialize
        patched_path = json_cache.with_suffix(".new.gz")
        with gzip.open(patched_path, "wb", compresslevel=3) as out:
            out.write(buf)

        response.body = gzip.open(patched_path)
        response.headers = response.headers

        return response
