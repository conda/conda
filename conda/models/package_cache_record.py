# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import ENOENT
from logging import getLogger
from os.path import basename, join

from .channel import Channel
from .._vendor.auxlib.decorators import memoizemethod
from ..base.constants import CONDA_TARBALL_EXTENSION

log = getLogger(__name__)


class PackageCacheRecord(object):

    @classmethod
    def make_legacy(cls, pkgs_dir, dist):
        # the dist object here should be created using a full url to the tarball
        extracted_package_dir = join(pkgs_dir, dist.dist_name)
        package_tarball_full_path = extracted_package_dir + CONDA_TARBALL_EXTENSION
        return cls(pkgs_dir, dist, package_tarball_full_path, extracted_package_dir)

    def __init__(self, pkgs_dir, dist, package_tarball_full_path, extracted_package_dir):
        # the channel object here should be created using a full url to the tarball
        self.pkgs_dir = pkgs_dir
        self.dist = dist
        self.package_tarball_full_path = package_tarball_full_path
        self.extracted_package_dir = extracted_package_dir
        self.channel = Channel(dist.to_url()) if dist.is_channel else Channel(None)

    @property
    def is_fetched(self):
        from ..gateways.disk.read import isfile
        return isfile(self.package_tarball_full_path)

    @property
    def is_extracted(self):
        from ..gateways.disk.read import isdir, isfile
        epd = self.extracted_package_dir
        return isdir(epd) and isfile(join(epd, 'info', 'index.json'))

    @property
    def tarball_basename(self):
        return basename(self.package_tarball_full_path)

    def tarball_matches_md5(self, md5sum):
        return self.md5sum == md5sum

    def tarball_matches_md5_if(self, md5sum):
        return not md5sum or self.md5sum == md5sum

    @property
    def package_cache_writable(self):
        from ..core.package_cache import PackageCache
        return PackageCache(self.pkgs_dir).is_writable

    @property
    def md5sum(self):
        repodata_record = self._get_repodata_record()
        if repodata_record is not None and repodata_record.md5:
            return repodata_record.md5
        elif self.is_fetched:
            return self._calculate_md5sum()
        else:
            return None

    def get_urls_txt_value(self):
        from ..core.package_cache import PackageCache
        return PackageCache(self.pkgs_dir).urls_data.get_url(self.package_tarball_full_path)

    @memoizemethod
    def _get_repodata_record(self):
        epd = self.extracted_package_dir

        try:
            from ..gateways.disk.read import read_repodata_json
            return read_repodata_json(epd)
        except (IOError, OSError) as ex:
            if ex.errno == ENOENT:
                return None
            raise  # pragma: no cover

    @memoizemethod
    def _calculate_md5sum(self):
        assert self.is_fetched
        from ..gateways.disk.read import compute_md5sum
        return compute_md5sum(self.package_tarball_full_path)

    def __repr__(self):
        args = ('%s=%r' % (key, getattr(self, key))
                for key in ('dist', 'package_tarball_full_path'))
        return "%s(%s)" % (self.__class__.__name__, ', '.join(args))
