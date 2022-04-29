#!/usr/bin/env python3
"""
Intercept requests for repodata.json, fulfill from cache or cache + patches
"""

import contextlib
import gzip
import json
import logging
import mimetypes
import os.path
import tempfile
import time
import hashlib
import jsonpatch
import appdirs
import bottle
import requests
import requests_cache
import re
import io
from urllib.parse import urlparse
from bottle import HTTPError, HTTPResponse, parse_date, request, route, run

from . import truncateable
from . import sync_jlap

log = logging.getLogger(__name__)

from pathlib import Path

CACHE_DIR = Path(appdirs.user_cache_dir("conda"))

# Patches will eventually be hosted at main URL
MIRROR_URL = "https://repodata.fly.dev"

CHUNK_SIZE = 1 << 14

session = sync_jlap.make_session((CACHE_DIR / "jlap_cache.db"))

sync = sync_jlap.SyncJlap(session, CACHE_DIR)


def hf(hash):
    """
    Abbreviate hash for formatting.
    """
    return hash[:16] + "\N{HORIZONTAL ELLIPSIS}"


def make_session():
    session = requests_cache.CachedSession(
        cache_control=True, allowable_codes=(200, 206), expire_after=300
    )
    session.headers["User-Agent"] = "update-conda-cache/0.0.1"
    return session


# mirrored on patch server
# should match repodata.json and current_repodata.json
# are ?= parameters ever used in conda?
supported = re.compile(
    r"https://((conda\.anaconda\.org/conda-forge|repo.anaconda.com/pkgs/main)/.*repodata.json)"
)


def hash_func(data: bytes = b""):
    return hashlib.blake2b(data, digest_size=32)


def conda_normalize_hash(data):
    """
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
            f"{hf(patch['from'])} \N{RIGHTWARDS ARROW} {hf(patch['to'])}, {len(patch['patch'])} steps"
        )
        data = jsonpatch.JsonPatch(patch["patch"]).apply(data, in_place=True)

    return data


@contextlib.contextmanager
def timeme(message=""):
    begin = time.time()
    yield
    end = time.time()
    log.debug(f"{message}{end-begin:0.02f}s")


def fetch_repodata_json(cache_path, upstream, session=requests):
    """
    Fetch new repodata.json; cache to a gzip'd file.

    Return (path, digest)
    """

    with tempfile.NamedTemporaryFile(dir=CACHE_DIR, delete=False) as outfile:
        compressed = gzip.open(outfile, "w")
        response = session.get(upstream, stream=True)
        response.raise_for_status()
        hash = hash_func()
        for chunk in response.iter_content(CHUNK_SIZE):
            hash.update(chunk)
            compressed.write(chunk)

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        compressed.close()
        os.replace(outfile.name, cache_path)

    return cache_path, hash.digest()


class DigestReader:
    """
    Read and hash at the same time.
    """

    def __init__(self, fp):
        self.fp = fp
        self.hash = hash_func()

    def read(self, bytes=None):
        buf = self.fp.read(bytes)
        self.hash.update(buf)
        return buf


def patch_files(cache_path: Path, jlap_path: Path):
    """
    Return patched version of cache_path, as a dict
    """
    jlap_lines = []
    with jlap_path.open("rb") as fp:
        jlap = truncateable.JlapReader(fp)
        jlap_lines = list(obj for obj, _ in jlap.readobjs())
        assert "latest" in jlap_lines[-1]

    meta = jlap_lines[-1]
    patches = jlap_lines[:-1]
    digest_reader = DigestReader(gzip.open(cache_path))
    original = json.load(digest_reader)
    assert digest_reader.read() == b""
    original_hash = digest_reader.hash.digest().hex()

    # XXX improve cache / re-download full file using standard cache rules
    if (original_hash != meta["latest"]) and not any(
        original_hash == patch["from"] for patch in patches
    ):
        log.info(
            f"Remove {cache_path} not found in patchset; {original_hash == meta['latest']} and not any 'from' hash"
        )
        cache_path.unlink()

    patched = apply_patches(original, patches, original_hash, meta["latest"])
    return patched


def patched_json(url):
    """
    Return cached repodata.json with latest patches applied, as a Response()
    """
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")  # we don't need the leading /
    server = parsed.hostname

    assert path.endswith("repodata.json")

    jlap_url = f"{MIRROR_URL}/{server}/{path[:-len('.json')]}.jlap"
    jlap_path = sync.update_url(jlap_url)

    cache_path = Path(CACHE_DIR / server / path).with_suffix(".json.gz")
    if not cache_path.exists():
        log.debug("Fetch complete %s", url)
        cache_path, digest = fetch_repodata_json(cache_path, url)
        assert digest  # check exists in patch file...

    # headers based on last modified of patch file
    response = static_file_headers(str(jlap_path.relative_to(CACHE_DIR)), root=CACHE_DIR)
    del response.headers["Content-Length"]

    if response.status_code != 200:  # file not found?
        return None

    log.debug("Serve from %s", cache_path)

    with timeme("Patch "):
        new_data = patch_files(cache_path, jlap_path)

    with timeme("Serialize "):
        buf = json.dumps(new_data).encode("utf-8")

    # TODO if cache is ok, read from here, skip patch, reserialize
    patched_path = cache_path.with_suffix(".new.gz")
    with gzip.open(patched_path, "wb", compresslevel=3) as out:
        out.write(buf)

    return {"body": gzip.open(patched_path), "headers": response.headers}


def send(request: requests.PreparedRequest, base_adapter):
    """
    request: PreparedRequest for original URL
    base_adapter: would accept the request, if we weren't
    """
    response_data = patched_json(request.url)
    response = requests.Response()
    response.request = request
    response.url = request.url
    response.status_code = 200
    response.headers.update(response_data["headers"])
    # a reader returning non-gzip'd bytes
    # gzip'd responses must be decompressed in a different layer...
    response.raw = response_data["body"]
    return response


def static_file_headers(
    filename, root, mimetype="auto", download=False, charset="UTF-8"
) -> bottle.BaseResponse:
    """
    bottle.static_file_headers but without opening file
    """

    root = os.path.abspath(root) + os.sep
    filename = os.path.abspath(os.path.join(root, filename.strip("/\\")))
    headers = dict()

    if not filename.startswith(root):
        return HTTPError(403, "Access denied.")
    if not os.path.exists(filename) or not os.path.isfile(filename):
        return HTTPError(404, "File does not exist.")
    if not os.access(filename, os.R_OK):
        return HTTPError(403, "You do not have permission to access this file.")

    if mimetype == "auto":
        mimetype, encoding = mimetypes.guess_type(filename)
        if encoding:
            headers["Content-Encoding"] = encoding

    if mimetype:
        if mimetype[:5] == "text/" and charset and "charset" not in mimetype:
            mimetype += "; charset=%s" % charset
        headers["Content-Type"] = mimetype

    if download:
        download = os.path.basename(filename if download == True else download)
        headers["Content-Disposition"] = 'attachment; filename="%s"' % download

    stats = os.stat(filename)
    headers["Content-Length"] = clen = stats.st_size
    lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
    headers["Last-Modified"] = lm

    ims = request.environ.get("HTTP_IF_MODIFIED_SINCE")
    if ims:
        ims = parse_date(ims.split(";")[0].strip())
    if ims is not None and ims >= int(stats.st_mtime):
        headers["Date"] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        return HTTPResponse(status=304, **headers)

    body = ""  # to be replaced

    return HTTPResponse(body, **headers)
