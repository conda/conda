#!/usr/bin/env python3
"""
Synchronize local patch files with repodata.fly.dev
"""

import os

from pathlib import Path
from requests_cache import CachedSession

from .no_cache import discard_serializer
from . import truncateable

import logging

log = logging.getLogger(__name__)


def make_session(db_path="http_cache_jlap"):
    session = CachedSession(
        str(db_path),
        allowable_codes=[200, 206],
        match_headers=["Accept", "Range"],
        serializer=discard_serializer,
        cache_control=True,
        expire_after=30,  # otherwise cache only expires if response header says so
    )
    session.headers["User-Agent"] = "update-conda-cache/0.0.1"
    return session


REPOS = [
    "repo.anaconda.com/pkgs/main",
    "conda.anaconda.org/conda-forge",
]

SUBDIRS = [
    "linux-64",
    "noarch",
    "osx-64",
    "osx-arm64",
    "win-64",
]

MIRROR = "repodata.fly.dev"

BASEDIR = Path("patches")


def line_offsets(path: Path):
    """
    Return byte offset to next-to-last line in path.
    """
    sum = 0
    offsets = []
    with path.open("rb") as data:
        for line in data:
            offsets.append(sum)
            sum += len(line)
    try:
        return offsets[-2]
    except IndexError:
        return 0


class SyncJlap:
    def __init__(self, session, basedir):
        self.session = session
        self.basedir = basedir

    def update_url(self, url):
        """
        Update local copy of .jlap file at url, fetching only latest lines.

        Return path to cached file.
        """
        session = self.session
        output = Path(self.basedir, url.split("://", 1)[-1])
        headers = {}
        if not output.exists():
            output.parent.mkdir(parents=True, exist_ok=True)
            headers = {"Cache-Control": "no-cache"}
        else:
            offset = line_offsets(output)
            headers = {"Range": "bytes=%d-" % offset}

        response = session.get(url, headers=headers)
        if response.from_cache:
            log.debug(f"from_cache {url} expires {response.expires}")
            return output

        log.debug(
            "%s %s %s %s",
            response.status_code,
            len(response.content),
            url,
            response.headers,
        )

        if response.status_code == 200:
            log.info("Full download")
            output.write_bytes(response.content)
        elif response.status_code == 206:
            size_before = os.stat(output).st_size
            os.truncate(output, offset)
            with output.open("ba") as out:
                tell = out.tell()
                log.info(
                    "Append %d-%d (%d lines)",
                    tell,
                    tell + len(response.content),
                    len(response.content.splitlines()),
                )
                out.write(response.content)
            size_after = os.stat(output).st_size
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
        with output.open("rb") as fp:
            jlap = truncateable.JlapReader(fp)
            for _obj in jlap.readobjs():
                pass

        return output


def update():
    sync = SyncJlap(make_session(), BASEDIR)

    for repo in REPOS:
        for subdir in SUBDIRS:
            for url in [
                f"https://{MIRROR}/{repo}/{subdir}/repodata.jlap",
                f"https://{MIRROR}/{repo}/{subdir}/current_repodata.jlap",
            ]:
                sync.update_url(url)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update()
