#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""
Intercept requests for repodata.json, fulfill from cache or cache + patches
"""

import gzip
import json
import logging
import mimetypes
import os
import tempfile
import time
import hashlib
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from typing import Optional, NamedTuple, Tuple

import requests
import jsonpatch

from conda.base import constants as consts

from . import truncateable


log = logging.getLogger(__name__)


def hf(hash_val):
    """
    Abbreviate hash for formatting.
    """
    return hash_val[:16] + "\N{HORIZONTAL ELLIPSIS}"


def hash_func(data: bytes = b"") -> hashlib.blake2b:
    return hashlib.blake2b(data, digest_size=32)


def conda_normalize_hash(data):
    """
    TODO: Not used; need to remove
    Normalize raw_data in the same way as conda-build index.py, return hash.
    """
    # serialization options used by conda-build's index.py
    # (conda should cache the unmodified response)
    data_buffer = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")

    data_hash = hash_func(data_buffer)
    data_hash.update(b"\n")  # conda_build/index.py _write_repodata adds newline
    data_hash = data_hash.hexdigest()

    return data_hash


def apply_patches(data, patches, have, want):
    apply = []
    for patch in reversed(patches):
        if have == want:
            break
        if patch["to"] == want:
            apply.append(patch)
            want = patch["from"]

    if have != want:
        log.info(f"No patch from local revision {hf(have)}")
        apply.clear()

    log.info(f"\nApply {len(apply)} patches {hf(have)} \N{RIGHTWARDS ARROW} {hf(want)}...")

    while apply:
        patch = apply.pop()
        log.info(
            f"{hf(patch['from'])} \N{RIGHTWARDS ARROW}"
            f" {hf(patch['to'])}, {len(patch['patch'])} steps"
        )
        data = jsonpatch.JsonPatch(patch["patch"]).apply(data, in_place=True)

    return data


def fetch_repodata_json(cache_path: Path, repodata_url: str, ses=None) -> Tuple[Path, str]:
    """
    Fetch new repodata.json; cache to a gzip'd file
    """
    if ses is None:
        ses = requests

    with tempfile.NamedTemporaryFile(dir=consts.CACHE_DIR, delete=False) as outfile:
        with gzip.open(outfile, "w") as compressed:
            response = ses.get(repodata_url, stream=True)
            response.raise_for_status()
            hash_val = hash_func()

            for chunk in response.iter_content(consts.JLAP_CHUNK_SIZE):
                hash_val.update(chunk)
                compressed.write(chunk)

            cache_path.parent.mkdir(parents=True, exist_ok=True)

        # tmpdir -> cache_dir
        os.replace(outfile.name, cache_path)

    return cache_path, hash_val.digest()


class DigestReader(NamedTuple):
    """
    Read and hash at the same time.
    """

    fp: gzip.GzipFile
    hash: hashlib.blake2b

    def read(self, bytes_val=None):
        buf = self.fp.read(bytes_val)
        self.hash.update(buf)

        return buf


def patch_files(cache_path: Path, jlap_path: Path):
    """
    Return patched version of cache_path, as a dict
    """
    with jlap_path.open("rb") as fp:
        jlap = truncateable.JlapReader(fp)
        jlap_lines = tuple(obj for obj, _ in jlap.read_objs())
        assert "latest" in jlap_lines[-1]

    meta = jlap_lines[-1]
    patches = jlap_lines[:-1]
    digest_reader = DigestReader(gzip.open(cache_path), hash_func())
    original = json.load(digest_reader)
    assert digest_reader.read() == b""
    original_hash = digest_reader.hash.digest().hex()

    # XXX improve cache / re-download full file using standard cache rules
    if (original_hash != meta["latest"]) and not any(
        original_hash == patch["from"] for patch in patches
    ):
        log.info(
            f"Removing {cache_path}; Not found in patchset;"
            f" {original_hash == meta['latest']} and not any 'from' hash"
        )
        cache_path.unlink()

    patched = apply_patches(original, patches, original_hash, meta["latest"])
    return patched


class RepodataUrl:
    """
    Stores repodata url parts and some handy methods for creating cache keys
    and jlap urls.
    """

    __slots__ = ("url", "url_obj", "path", "server")

    def __init__(self, repodata_url):
        self.url = repodata_url
        self.url_obj = urlparse(self.url)
        self.path = self.url_obj.path.lstrip("/")
        self.server = self.url_obj.hostname

    def get_cache_repodata_gzip_key(self) -> Path:
        """Used to determine the place where this cache will be stored"""
        return Path(consts.CACHE_DIR / self.server / self.path).with_suffix(".json.gz")

    def get_cache_repodata_jlap_key(self) -> Path:
        """Used to determine the place where this cache will be stored"""
        url = self.translate_to_jlap_url()
        return Path(consts.CACHE_DIR, url.split("://", 1)[-1])

    def translate_to_jlap_url(self) -> str:
        """translates our repodata_url into a jlap one."""
        assert self.path.endswith(consts.REPODATA_FN)  # TODO: remove the assert statement
        return urlunparse(self.url_obj._replace(path=self.path[:-len('.json')] + ".jlap"))


class FileResponse(NamedTuple):
    status_code: Optional[int]
    body: Optional[str]
    headers: Optional[dict]


def static_file_headers(
    filename: str,
    root: str,
    mimetype: str = "auto",
    download: bool = False,
    charset: str = "utf-8",
) -> FileResponse:
    """
    Returns a "FileResponse" response that is supposed to mimic an HTTP response
    This is why these responses have headers and status codes.
    """
    root = os.path.abspath(root) + os.path.sep
    filename = os.path.abspath(os.path.join(root, filename.strip("/\\")))
    headers = dict()

    if not filename.startswith(root):
        return FileResponse(status_code=403, body="Access denied.", headers=headers)
    if not os.path.exists(filename) or not os.path.isfile(filename):
        return FileResponse(status_code=404, body="File does not exist.", headers=headers)
    if not os.access(filename, os.R_OK):
        return FileResponse(
            status_code=403,
            body="You do not have permission to access this file.",
            headers=headers,
        )

    if mimetype == "auto":
        mimetype, encoding = mimetypes.guess_type(filename)
        if encoding:
            headers["Content-Encoding"] = encoding

    if mimetype:
        if mimetype.startswith("text/") and charset and "charset" not in mimetype:
            mimetype += "; charset=%s" % charset
        headers["Content-Type"] = mimetype

    if download:
        download = os.path.basename(filename if download is True else download)
        headers["Content-Disposition"] = 'attachment; filename="%s"' % download

    stats = os.stat(filename)
    headers["Content-Length"] = stats.st_size
    lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
    headers["Last-Modified"] = lm

    # if the response was cached, the caller should already have downloaded the
    # response body.
    body = ""

    return FileResponse(body=body, headers=headers, status_code=200)
