# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Interface between conda-content-trust and conda."""
import json
import warnings
from functools import lru_cache
from glob import glob
from logging import getLogger
from os import makedirs
from os.path import basename, exists, isdir, join

try:
    from conda_content_trust.authentication import verify_delegation, verify_root
    from conda_content_trust.common import (
        SignatureError,
        load_metadata_from_file,
        write_metadata_to_file,
    )
    from conda_content_trust.signing import wrap_as_signable
except ImportError:
    # _SignatureVerification.enabled handles the rest of this state
    class SignatureError(Exception):
        pass


from ..base.constants import CONDA_PACKAGE_EXTENSION_V1, CONDA_PACKAGE_EXTENSION_V2
from ..base.context import context
from ..common.url import join_url
from ..core.subdir_data import SubdirData
from ..gateways.connection import HTTPError, InsecureRequestWarning
from ..gateways.connection.session import get_session
from ..models.records import PackageRecord
from .constants import INITIAL_TRUST_ROOT, KEY_MGR_FILE

log = getLogger(__name__)


class _SignatureVerification:
    # FUTURE: Python 3.8+, replace with functools.cached_property
    @property
    @lru_cache(maxsize=None)
    def enabled(self):
        # safety checks must be enabled
        if not context.extra_safety_checks:
            return False

        # signing url must be defined
        if not context.signing_metadata_url_base:
            log.warn(
                "metadata signature verification requested, "
                "but no metadata URL base has not been specified."
            )
            return False

        # conda_content_trust must be installed
        try:
            import conda_content_trust  # noqa: F401
        except ImportError:
            log.warn(
                "metadata signature verification requested, "
                "but `conda-content-trust` is not installed."
            )
            return False

        # create artifact verification directory if missing
        if not isdir(context.av_data_dir):
            log.info("creating directory for artifact verification metadata")
            makedirs(context.av_data_dir)

        # ensure the trusted_root exists
        if self.trusted_root is None:
            log.warn(
                "could not find trusted_root data for metadata signature verification"
            )
            return False

        # ensure the key_mgr exists
        if self.key_mgr is None:
            log.warn("could not find key_mgr data for metadata signature verification")
            return False

        # signature verification is enabled
        return True

    # FUTURE: Python 3.8+, replace with functools.cached_property
    @property
    @lru_cache(maxsize=None)
    def trusted_root(self):
        # TODO: formalize paths for `*.root.json` and `key_mgr.json` on server-side
        trusted = INITIAL_TRUST_ROOT

        # Load current trust root metadata from filesystem
        for path in sorted(
            glob(join(context.av_data_dir, "[0-9]*.root.json")), reverse=True
        ):
            try:
                int(basename(path).split(".")[0])
            except ValueError:
                # prefix is not an int and is consequently an invalid file, skip to the next
                pass
            else:
                log.info(f"Loading root metadata from {path}.")
                trusted = load_metadata_from_file(path)
                break
        else:
            log.debug(
                f"No root metadata in {context.av_data_dir}. "
                "Using built-in root metadata."
            )

        # Refresh trust root metadata
        more_signatures = True
        while more_signatures:
            # TODO: caching mechanism to reduce number of refresh requests
            fname = f"{trusted['signed']['version'] + 1}.root.json"
            path = join(context.av_data_dir, fname)

            try:
                # TODO: support fetching root data with credentials
                untrusted = self._fetch_channel_signing_data(
                    context.signing_metadata_url_base,
                    fname,
                )

                verify_root(trusted, untrusted)
            except HTTPError as err:
                # HTTP 404 implies no updated root.json is available, which is
                # not really an "error" and does not need to be logged.
                if err.response.status_code != 404:
                    log.error(err)
                more_signatures = False
            except Exception as err:
                # TODO: more error handling
                log.error(err)
                more_signatures = False
            else:
                # New trust root metadata checks out
                trusted = untrusted
                write_metadata_to_file(trusted, path)

        return trusted

    # FUTURE: Python 3.8+, replace with functools.cached_property
    @property
    @lru_cache(maxsize=None)
    def key_mgr(self):
        trusted = None

        # Refresh key manager metadata
        fname = KEY_MGR_FILE
        path = join(context.av_data_dir, fname)

        try:
            untrusted = self._fetch_channel_signing_data(
                context.signing_metadata_url_base,
                KEY_MGR_FILE,
            )

            verify_delegation("key_mgr", untrusted, self.trusted_root)
        except (ConnectionError, HTTPError) as err:
            log.warn(err)
        except Exception as err:
            # TODO: more error handling
            raise
            log.error(err)
        else:
            # New key manager metadata checks out
            trusted = untrusted
            write_metadata_to_file(trusted, path)

        # If key_mgr is unavailable from server, fall back to copy on disk
        if not trusted and exists(path):
            trusted = load_metadata_from_file(path)

        return trusted

    def _fetch_channel_signing_data(
        self, signing_data_url, filename, etag=None, mod_stamp=None
    ):
        session = get_session(signing_data_url)

        if not context.ssl_verify:
            warnings.simplefilter("ignore", InsecureRequestWarning)

        headers = {
            "Accept-Encoding": "gzip, deflate, compress, identity",
            "Content-Type": "application/json",
        }
        if etag:
            headers["If-None-Match"] = etag
        if mod_stamp:
            headers["If-Modified-Since"] = mod_stamp

        saved_token_setting = context.add_anaconda_token
        try:
            # Assume trust metadata is intended to be "generally available",
            # and specifically, _not_ protected by a conda/binstar token.
            # Seems reasonable, since we (probably) don't want the headaches of
            # dealing with protected, per-channel trust metadata.
            #
            # Note: Setting `auth=None` here does allow trust metadata to be
            # protected using standard HTTP basic auth mechanisms, with the
            # login information being provided in the user's netrc file.
            context.add_anaconda_token = False
            resp = session.get(
                join_url(signing_data_url, filename),
                headers=headers,
                proxies=session.proxies,
                auth=None,
                timeout=(
                    context.remote_connect_timeout_secs,
                    context.remote_read_timeout_secs,
                ),
            )
            # TODO: maybe add more sensible error handling
            resp.raise_for_status()
        finally:
            context.add_anaconda_token = saved_token_setting

        # In certain cases (e.g., using `-c` access anaconda.org channels), the
        # `CondaSession.get()` retry logic combined with the remote server's
        # behavior can result in non-JSON content being returned.  Parse returned
        # content here (rather than directly in the return statement) so callers of
        # this function only have to worry about a ValueError being raised.
        try:
            return resp.json()
        except json.decoder.JSONDecodeError as err:  # noqa
            # TODO: additional loading and error handling improvements?
            raise ValueError(
                f"Invalid JSON returned from {signing_data_url}/{filename}"
            )

    def verify(self, record: PackageRecord):
        repodata, _ = SubdirData(record.channel).repo_fetch.fetch_latest_parsed()

        if "signatures" not in repodata:
            raise SignatureError("no signatures found in repodata")
        signatures = repodata["signatures"]

        if record.fn not in signatures:
            raise SignatureError(f"no signature found for {record.fn}")
        signature = signatures[record.fn]

        if record.fn.endswith(CONDA_PACKAGE_EXTENSION_V1):
            info = repodata["packages"][record.fn]
        elif record.fn.endswith(CONDA_PACKAGE_EXTENSION_V2):
            info = repodata["packages.conda"][record.fn]
        else:
            raise ValueError("unknown package extension")

        # create a signable envelope (a dict with the info and signatures)
        envelope = wrap_as_signable(info)
        envelope["signatures"] = signature

        try:
            verify_delegation("pkg_mgr", envelope, self.key_mgr)
        except SignatureError:
            log.warning(f"invalid signature for {record.fn}")
            record.metadata.add("(package metadata is UNTRUSTED)")
        else:
            log.info(f"valid signature for {record.fn}")
            record.metadata.add("(package metadata is TRUSTED)")

    def __call__(
        self,
        unlink_precs: tuple[PackageRecord, ...],
        link_precs: tuple[PackageRecord, ...],
    ) -> None:
        if not self.enabled:
            return

        for prec in link_precs:
            self.verify(prec)


# singleton for caching
signature_verification = _SignatureVerification()
