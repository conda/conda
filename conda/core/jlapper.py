# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Lappin' up the jlap
from __future__ import annotations

import json
import logging
import pathlib
import pprint
import re
import sys
import time
from contextlib import contextmanager
from hashlib import blake2b
from typing import Iterator

import jsonpatch
from requests import HTTPError

from conda.base.context import context
from conda.gateways.connection import Response, Session
from conda.gateways.connection.session import CondaSession

log = logging.getLogger(__name__)


DIGEST_SIZE = 32  # 160 bits a minimum 'for security' length?
MAX_LINEID_BYTES = 64

JLAP = "jlap"
HEADERS = "headers"
NOMINAL_HASH = "have"
ON_DISK_HASH = "have_hash"
LATEST = "latest"
JLAP_UNAVAILABLE = "jlap_unavailable"


def bhfunc(data: bytes, key: bytes):
    """
    Keyed hash.
    """
    return blake2b(data, key=key, digest_size=DIGEST_SIZE)


def hfunc():
    """
    Ordinary hash.
    """
    return blake2b(digest_size=DIGEST_SIZE)


def get_place(url, extra=""):
    from .repo_jlap import console

    console.print_json(data=dict(url=url, extra=extra))
    if "current_repodata" in url:
        extra = f".c{extra}"
    return pathlib.Path("-".join(url.split("/")[-3:-1])).with_suffix(f"{extra}.json")


def line_and_pos(response: Response, pos=0) -> Iterator[tuple[int, bytes]]:
    for line in response.iter_lines(delimiter=b"\n"):
        # iter_lines yields either bytes or str
        yield pos, line  # type: ignore
        pos += len(line) + 1


def fetch_jlap(url, pos=0, etag=None, iv=b"", ignore_etag=True):
    session = CondaSession()
    response = request_jlap(url, pos=pos, etag=etag, ignore_etag=ignore_etag, session=session)
    return process_jlap_response(response, pos=pos, iv=iv)


def request_jlap(url, pos=0, etag=None, ignore_etag=True, session: Session | None = None):
    # XXX max-age seconds; return dummy buffer if 304 not modified?
    headers = {}
    if pos:
        headers["range"] = f"bytes={pos}-"
    if etag and not ignore_etag:
        headers["if-none-match"] = etag

    log.info("%s", headers)

    if session is None:
        session = CondaSession()

    timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
    response = session.get(url, stream=True, headers=headers, timeout=timeout)
    response.raise_for_status()

    if "range" in headers:
        log.debug("request headers: %s", pprint.pformat(response.request.headers))
        log.debug(
            "response headers: %s",
            pprint.pformat(
                {
                    k: v
                    for k, v in response.headers.items()
                    if any(map(k.lower().__contains__, ("content", "last", "range", "encoding")))
                }
            ),
        )
        pprint.pprint("status: %d" % response.status_code)
        assert response.status_code == 206, "server returned full response"

    log.info("%s", response)

    return response


def process_jlap_response(response, pos=0, iv=b""):
    # save initial iv in case there were no new lines
    # maybe unless pos==0
    buffer: list[tuple[int, str, str]] = [(-1, iv.hex(), iv.hex())]
    initial_pos = pos

    for pos, line in line_and_pos(response, pos=pos):
        if pos == 0:
            iv = bytes.fromhex(line.decode("utf-8"))
            buffer = [(0, iv.hex(), iv.hex())]
        else:
            iv = bhfunc(line, iv).digest()
            buffer.append((pos, line.decode("utf-8"), iv.hex()))

    log.info("%d bytes read", pos - initial_pos)  # maybe + length of last line

    if buffer[-1][1] != buffer[-2][-1]:
        # pprint.pprint(buffer[-10:])
        # dump to file?
        raise ValueError("checksum mismatch")
    else:
        log.info("Checksum OK")

    # new iv == initial iv if nothing changed
    pos, footer, not_iv = buffer[-2]
    footer = json.loads(footer)

    new_state = {
        "headers": {k.lower(): v for k, v in response.headers.items()},
        "iv": buffer[-3][-1],
        "pos": pos,
        "footer": footer,
    }

    return buffer, new_state


def hf(hash):
    """
    Abbreviate hash for formatting.
    """
    return hash[:16] + "\N{HORIZONTAL ELLIPSIS}"


def find_patches(patches, have, want):
    apply = []
    for patch in reversed(patches):
        if have == want:
            break
        if patch["to"] == want:
            log.info("Collect %s \N{LEFTWARDS ARROW} %s", hf(want), hf(patch["from"]))
            apply.append(patch)
            want = patch["from"]

    if have != want:
        print(f"No patch from local revision {hf(have)}")
        raise LookupError("patch not found")

    return apply


def apply_patches(data, apply):
    while apply:
        patch = apply.pop()
        print(
            f"{hf(patch['from'])} \N{RIGHTWARDS ARROW} {hf(patch['to'])}, "
            f"{len(patch['patch'])} steps"
        )
        data = jsonpatch.JsonPatch(patch["patch"]).apply(data, in_place=True)


def withext(url, ext):
    return re.sub(r"(\.\w+)$", ext, url)


@contextmanager
def timeme(message):
    begin = time.monotonic()
    yield
    end = time.monotonic()
    log.info("%sTook %0.02fs", message, end - begin)


def download_and_hash(hasher, url, json_path, session: Session):
    """
    Download url if it doesn't exist, passing bytes through hasher.update()
    """
    timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
    response = session.get(url, stream=True, timeout=timeout)
    response.raise_for_status()
    length = 0
    with json_path.open("wb") as repodata:
        for block in response.iter_content():
            hasher.update(block)
            repodata.write(block)
            length += len(block)
    if response.request:
        log.info("Download %d bytes %r", length, response.request.headers)


def request_url_jlap(url, get_place=get_place, full_download=False):
    """
    Complete save complete json / save place / update with jlap sequence.
    """
    state_path = get_place(url, ".s")
    try:
        state = json.loads(state_path.read_text())
    except FileNotFoundError:
        state = {}

    request_url_jlap_state(url, state, get_place=get_place, full_download=False)

    state = {k: v for k, v in state.items() if k in (NOMINAL_HASH, ON_DISK_HASH, JLAP)}

    state_path.write_text(json.dumps(state, indent=True))


def request_url_jlap_state(
    url, state: dict, get_place=get_place, full_download=False, session: Session | None = None
):
    if session is None:
        session = CondaSession()

    jlap_state = state.get(JLAP, {})
    headers = jlap_state.get(HEADERS, {})

    json_path = get_place(url)

    buffer = []  # type checks

    if (
        full_download
        or not (NOMINAL_HASH in state and json_path.exists())
        or state.get(JLAP_UNAVAILABLE)
    ):
        hasher = hfunc()
        with timeme("Download "):
            # TODO use Etag, Last-Modified caching headers if file exists
            # otherwise we re-download every time, if jlap is unavailable.
            download_and_hash(hasher, withext(url, ".json"), json_path, session=session)

        have = state[NOMINAL_HASH] = state[ON_DISK_HASH] = hasher.hexdigest()

        # trick code even though there is no jlap yet? buffer with zero patches.
        buffer = [[-1, b"", ""], [0, json.dumps({LATEST: have}), ""], [1, b"", ""]]

    else:
        have = state[NOMINAL_HASH]
        # have_hash = state.get(ON_DISK_HASH)

        need_jlap = True
        try:
            # wrong to read state outside of function, and totally rebuild inside
            buffer, jlap_state = fetch_jlap(
                withext(url, ".jlap"),
                pos=jlap_state.get("pos", 0),
                etag=headers.get("etag", None),
                iv=bytes.fromhex(jlap_state.get("iv", "")),
            )
            need_jlap = False
        except ValueError:
            log.info("Checksum not OK")
        except HTTPError as e:
            # If we get a 416 Requested range not satisfiable, the server-side
            # file may have been truncated and we need to fetch from 0
            if e.response.status_code == 404:
                state[JLAP_UNAVAILABLE] = time.time()
                return request_url_jlap_state(url, state, get_place=get_place, full_download=True)
            log.exception("Requests error")

        if need_jlap:  # retry for some reason
            buffer, jlap_state = fetch_jlap(withext(url, ".jlap"))

        get_place(url).with_suffix(".jlap").write_text("\n".join(b[1] for b in buffer))

        state["jlap"] = jlap_state

    with timeme("Apply Patches "):
        # buffer[0] == previous iv
        # buffer[1:-2] == patches
        # buffer[-2] == footer = new_state["footer"]
        # buffer[-1] == trailing checksum

        patches = list(json.loads(patch) for _, patch, _ in buffer[1:-2])
        want = json.loads(buffer[-2][1])["latest"]

        try:
            apply = find_patches(patches, have, want)
            log.info(f"Apply {len(apply)} patches {hf(have)} \N{RIGHTWARDS ARROW} {hf(want)}")

            if apply:
                with timeme("Load "), json_path.open() as repodata:
                    repodata_json = json.load(repodata)  # check have_hash here
                    # if this fails, then we also need to fetch again from 0

                apply_patches(repodata_json, apply)

                with timeme("Write changed "), json_path.open("wb") as repodata:

                    hasher = hfunc()

                    class hashwriter:
                        def write(self, s):
                            b = s.encode("utf-8")
                            hasher.update(b)
                            return repodata.write(b)

                    # faster than dump(obj, fp)
                    hashwriter().write(json.dumps(repodata_json))

                    # actual hash of serialized json
                    state["have_hash"] = hasher.hexdigest()

                    # hash of equivalent upstream json
                    state["have"] = want

            else:
                assert state["have"] == want

        except LookupError as e:
            if e.args[0] != "patch not found":
                raise

            # 'have' hash not mentioned in patchset
            #
            # XXX or skip jlap at top of fn; make sure it is not
            # possible to download the complete json twice
            log.info("Current repodata.json %s not found in patchset. Re-download repodata.json")

            assert not full_download, "Recursion error"

            # XXX debugging
            json_new_path = json_path.with_suffix(".json.old")
            log.warning("Rename to %s for debugging", json_new_path)
            json_path.rename(json_new_path)
            return request_url_jlap(url, get_place=get_place, full_download=True)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=logging.INFO,
    )
    log.setLevel(logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.INFO)

    for url in [
        "https://conda.anaconda.org/conda-forge/linux-64/current_repodata.json",
        "https://conda.anaconda.org/conda-forge/linux-64/repodata.json",
        "https://conda.anaconda.org/conda-forge/linux-aarch64/current_repodata.json",
        "https://conda.anaconda.org/conda-forge/linux-aarch64/repodata.json",
        "https://repo.anaconda.com/pkgs/main/osx-64/current_repodata.json",
        "https://repo.anaconda.com/pkgs/main/osx-64/repodata.json",
    ]:
        if len(sys.argv) > 1:
            if sys.argv[1] not in url:
                # print(f"Skip {url}")
                continue

        # curl --compressed produces weak etag

        log.info("Fetch with jlap %s", url)
        request_url_jlap(url)
