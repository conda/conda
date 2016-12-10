# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from abc import ABCMeta, abstractmethod, abstractproperty
import json
from logging import getLogger
from os.path import dirname, join

from .linked_data import delete_linked_data, load_linked_data
from .portability import _PaddingError, update_prefix
from .._vendor.auxlib.compat import with_metaclass
from .._vendor.auxlib.ish import dals
from ..base.context import context
from ..common.compat import iteritems, on_win
from ..common.path import get_bin_directory_short_path, get_python_path, url_to_path, win_path_ok
from ..common.url import path_to_url
from ..exceptions import CondaVerificationError, PaddingError
from ..gateways.disk.create import (compile_pyc, create_hard_link_or_copy, create_link,
                                    create_private_envs_meta, create_private_pkg_entry_point,
                                    create_unix_entry_point, create_windows_entry_point_py,
                                    extract_tarball, make_menu, remove_private_envs_meta,
                                    write_conda_meta_record)
from ..gateways.disk.delete import rm_rf, try_rmdir_all_empty
from ..gateways.disk.read import compute_md5sum, exists, isfile, islink
from ..gateways.disk.update import backoff_rename
from ..gateways.download import download
from ..models.dist import Dist
from ..models.enums import LinkType
from ..models.record import Record

log = getLogger(__name__)


REPR_IGNORE_KWARGS = (
    'transaction_context',
    'package_info',
)

@with_metaclass(ABCMeta)
class PathAction(object):

    _verified = False

    @abstractmethod
    def verify(self):
        raise NotImplementedError()

    @abstractmethod
    def execute(self):
        raise NotImplementedError()

    @abstractmethod
    def reverse(self):
        raise NotImplementedError()

    @abstractmethod
    def cleanup(self):
        raise NotImplementedError()

    @abstractproperty
    def target_full_path(self):
        raise NotImplementedError()

    @property
    def verified(self):
        return self._verified

    def __repr__(self):
        args = ('%s=%r' % (key, value) for key, value in iteritems(vars(self))
                if key not in REPR_IGNORE_KWARGS)
        return "%s(%s)" % (self.__class__.__name__, ', '.join(args))


@with_metaclass(ABCMeta)
class PrefixPathAction(PathAction):

    def __init__(self, transaction_context, target_prefix, target_short_path):
        self.transaction_context = transaction_context
        self.target_prefix = target_prefix
        self.target_short_path = target_short_path

    @property
    def target_full_path(self):
        trgt, shrt_pth = self.target_prefix, self.target_short_path
        return join(trgt, win_path_ok(shrt_pth)) if trgt and shrt_pth else None


# ######################################################
#  Prefix Creation Actions
# ######################################################

@with_metaclass(ABCMeta)
class CreatePrefixPathAction(PrefixPathAction):
    # All CreatePathAction subclasses must create a SINGLE new path
    #   the short/in-prefix version of that path must be returned by execute()

    def __init__(self, transaction_context, package_info, source_prefix, source_short_path,
                 target_prefix, target_short_path):
        super(CreatePrefixPathAction, self).__init__(transaction_context,
                                                     target_prefix, target_short_path)
        self.package_info = package_info
        self.source_prefix = source_prefix
        self.source_short_path = source_short_path

    def verify(self):
        self._verified = True

    def cleanup(self):
        # create actions typically won't need cleanup
        pass

    @property
    def source_full_path(self):
        prfx, shrt_pth = self.source_prefix, self.source_short_path
        return join(prfx, win_path_ok(shrt_pth)) if prfx and shrt_pth else None


class LinkPathAction(CreatePrefixPathAction):

    def __init__(self, transaction_context, package_info,
                 extracted_package_dir, source_short_path,
                 target_prefix, target_short_path, link_type):
        super(LinkPathAction, self).__init__(transaction_context, package_info,
                                             extracted_package_dir, source_short_path,
                                             target_prefix, target_short_path)
        self.link_type = link_type

    def verify(self):
        # TODO: consider checking hashsums
        if self.link_type != LinkType.directory and not exists(self.source_full_path):
            raise CondaVerificationError(dals("""
            The package for %s located at %s
            appears to be corrupted. The path '%s'
            specified in the package manifest cannot be found.
            """ % (self.package_info.index_json_record.name,
                   self.package_info.extracted_package_dir,
                   self.source_short_path)))
        self._verified = True

    def execute(self):
        log.trace("linking %s => %s", self.source_full_path, self.target_full_path)
        create_link(self.source_full_path, self.target_full_path, self.link_type,
                    force=context.force)

    def reverse(self):
        if self.link_type == LinkType.directory:
            try_rmdir_all_empty(self.target_full_path)
        else:
            rm_rf(self.target_full_path)


class PrefixReplaceLinkAction(LinkPathAction):

    def __init__(self, transaction_context, package_info,
                 extracted_package_dir, source_short_path,
                 target_prefix, target_short_path, prefix_placeholder, file_mode):
        super(PrefixReplaceLinkAction, self).__init__(transaction_context, package_info,
                                                      extracted_package_dir, source_short_path,
                                                      target_prefix, target_short_path,
                                                      LinkType.copy)
        self.prefix_placeholder = prefix_placeholder
        self.file_mode = file_mode

    def verify(self):
        if not (self.prefix_placeholder or self.file_mode):
            raise CondaVerificationError(dals("""
            The package for %s located at %s
            appears to be corrupted. For the file at path %s
            a prefix_placeholder and file_mode must be specified. Instead got values
            of '%s' and '%s'.
            """ % (self.package_info.index_json_record.name,
                   self.package_info.extracted_package_dir,
                   self.source_short_path, self.prefix_placeholder, self.file_mode)))
        if not isfile(self.source_full_path):
            raise CondaVerificationError(dals("""
            The package for %s located at %s
            appears to be corrupted. The path '%s'
            specified in the package manifest is not a file.
            """ % (self.package_info.index_json_record.name,
                   self.package_info.extracted_package_dir,
                   self.source_short_path)))
        self._verified = True

    def execute(self):
        super(PrefixReplaceLinkAction, self).execute()
        if islink(self.source_full_path):
            log.trace("ignoring prefix update for symlink with source path %s",
                      self.source_full_path)
            return

        try:
            log.trace("rewriting prefixes in %s", self.target_full_path)
            update_prefix(self.target_full_path, self.target_prefix, self.prefix_placeholder,
                          self.file_mode)
        except _PaddingError:
            raise PaddingError(self.target_full_path, self.prefix_placeholder,
                               len(self.prefix_placeholder))


class MakeMenuAction(CreatePrefixPathAction):

    def __init__(self, transaction_context, package_info,
                 target_prefix, target_short_path):
        super(MakeMenuAction, self).__init__(transaction_context, package_info,
                                             None, None, target_prefix, target_short_path)

    def execute(self):
        log.trace("making menu for %s", self.target_full_path)
        make_menu(self.target_prefix, self.target_short_path, remove=False)

    def reverse(self):
        log.trace("removing menu for %s", self.target_full_path)
        make_menu(self.target_prefix, self.target_short_path, remove=True)


class CompilePycAction(CreatePrefixPathAction):

    def __init__(self, transaction_context, package_info, target_prefix,
                 source_short_path, target_short_path):
        super(CompilePycAction, self).__init__(transaction_context, package_info,
                                               target_prefix, source_short_path,
                                               target_prefix, target_short_path)

    def execute(self):
        log.trace("compiling %s", self.target_full_path)
        python_short_path = get_python_path(self.transaction_context['target_python_version'])
        python_full_path = join(self.target_prefix, win_path_ok(python_short_path))
        compile_pyc(python_full_path, self.source_full_path)

    def reverse(self):
        rm_rf(self.target_full_path)


class CreatePythonEntryPointAction(CreatePrefixPathAction):

    def __init__(self, transaction_context, package_info, target_prefix, target_short_path,
                 module, func):
        super(CreatePythonEntryPointAction, self).__init__(transaction_context, package_info,
                                                           None, None,
                                                           target_prefix, target_short_path)
        self.module = module
        self.func = func

    def execute(self):
        log.trace("creating python entry point %s", self.target_full_path)
        if on_win:
            create_windows_entry_point_py(self.target_full_path, self.module, self.func)
        else:
            python_short_path = get_python_path(self.transaction_context['target_python_version'])
            python_full_path = join(self.target_prefix, win_path_ok(python_short_path))
            create_unix_entry_point(self.target_full_path, python_full_path,
                                    self.module, self.func)

    def reverse(self):
        rm_rf(self.target_full_path)


class CreateApplicationEntryPointAction(CreatePrefixPathAction):

    def __init__(self, transaction_context, package_info, target_prefix, target_short_path,
                 private_env_prefix, app_name, root_prefix):
        super(CreateApplicationEntryPointAction, self).__init__(transaction_context, package_info,
                                                                None, None, target_prefix,
                                                                target_short_path)
        self.private_env_prefix = private_env_prefix
        self.app_name = app_name
        self.root_preifx = root_prefix

    def execute(self):
        log.trace("creating application entry point %s", self.target_full_path)
        python_short_path = get_python_path(self.transaction_context['target_python_version'])
        python_full_path = join(self.root_preifx, win_path_ok(python_short_path))
        source_full_path = join(self.private_env_prefix, get_bin_directory_short_path(),
                                self.app_name)
        create_private_pkg_entry_point(self.target_full_path, python_full_path, source_full_path)

    def reverse(self):
        rm_rf(self.target_full_path)


class CreateCondaMetaAction(CreatePrefixPathAction):

    def __init__(self, transaction_context, package_info, target_prefix, meta_record):
        target_short_path = 'conda-meta/' + Dist(package_info).to_filename('.json')
        super(CreateCondaMetaAction, self).__init__(transaction_context, package_info,
                                                    None, None, target_prefix, target_short_path)
        self.meta_record = meta_record

    def execute(self):
        log.trace("creating conda-meta %s", self.target_full_path)
        write_conda_meta_record(self.target_prefix, self.meta_record)
        load_linked_data(self.target_prefix, Dist(self.package_info.repodata_record).dist_name,
                         self.meta_record)

    def reverse(self):
        delete_linked_data(self.target_prefix, Dist(self.package_info.repodata_record),
                           delete=False)
        rm_rf(self.target_full_path)


class CreatePrivateEnvMetaAction(CreatePrefixPathAction):
    def __init__(self, transaction_context, package_info, target_prefix):
        target_short_path = 'conda-meta/private_envs'
        super(CreatePrivateEnvMetaAction, self).__init__(transaction_context, package_info,
                                                         None, None, target_prefix,
                                                         target_short_path)

    def execute(self):
        log.trace("creating private env entry for '%s' in %s",
                  self.package_info.repodata_record.name, self.target_full_path)
        # TODO: need to capture old env entry if it was there, so that it can be reversed
        name = "%s-%s" % (self.package_info.repodata_record.name,
                          self.package_info.repodata_record.version)
        create_private_envs_meta(name, context.root_prefix, self.target_prefix)

    def reverse(self):
        log.trace("reversing private env entry for '%s' in %s",
                  self.package_info.repodata_record.name, self.target_full_path)
        remove_private_envs_meta(self.package_info.repodata_record.name)


# ######################################################
#  Prefix Removal Actions
# ######################################################

@with_metaclass(ABCMeta)
class RemovePrefixPathAction(PrefixPathAction):

    def __init__(self, transaction_context, linked_package_data, target_prefix, target_short_path):
        super(RemovePrefixPathAction, self).__init__(transaction_context,
                                                     target_prefix, target_short_path)
        self.linked_package_data = linked_package_data

    def verify(self):
        # inability to remove will trigger a rollback
        # can't definitely know if path can be removed until it's attempted and failed
        self._verified = True


class UnlinkPathAction(RemovePrefixPathAction):
    def __init__(self, transaction_context, linked_package_data, target_prefix, target_short_path,
                 link_type=LinkType.hardlink):
        super(UnlinkPathAction, self).__init__(transaction_context, linked_package_data,
                                               target_prefix, target_short_path)
        conda_temp_extension = '.c~'
        self.holding_short_path = self.target_short_path + conda_temp_extension
        self.holding_full_path = self.target_full_path + conda_temp_extension
        self.link_type = link_type

    def execute(self):
        if self.link_type != LinkType.directory:
            log.trace("renaming %s => %s", self.target_short_path, self.holding_short_path)
            backoff_rename(self.target_full_path, self.holding_full_path)

    def reverse(self):
        if self.link_type != LinkType.directory and exists(self.holding_full_path):
            log.trace("reversing rename %s => %s", self.holding_short_path, self.target_short_path)
            backoff_rename(self.holding_full_path, self.target_full_path)

    def cleanup(self):
        if self.link_type == LinkType.directory:
            try_rmdir_all_empty(self.target_full_path)
        else:
            rm_rf(self.holding_full_path)


class RemoveMenuAction(RemovePrefixPathAction):

    def __init__(self, transaction_context, linked_package_data,
                 target_prefix, target_short_path):
        super(RemoveMenuAction, self).__init__(transaction_context, linked_package_data,
                                               target_prefix, target_short_path)

    def execute(self):
        log.trace("removing menu for %s ", self.target_prefix)
        make_menu(self.target_prefix, self.target_short_path, remove=True)

    def reverse(self):
        log.trace("re-creating menu for %s ", self.target_prefix)
        make_menu(self.target_prefix, self.target_short_path, remove=False)

    def cleanup(self):
        pass


class RemoveCondaMetaAction(UnlinkPathAction):

    def __init__(self, transaction_context, linked_package_data, target_prefix, target_short_path):
        super(RemoveCondaMetaAction, self).__init__(transaction_context, linked_package_data,
                                                    target_prefix, target_short_path)

    def execute(self):
        super(RemoveCondaMetaAction, self).execute()
        delete_linked_data(self.target_prefix, Dist(self.linked_package_data),
                           delete=False)

    def reverse(self):
        super(RemoveCondaMetaAction, self).reverse()
        with open(self.target_full_path, 'r') as fh:
            meta_record = Record(**json.loads(fh.read()))
        log.trace("reloading cache entry %s", self.target_full_path)
        load_linked_data(self.target_prefix,
                         Dist(self.linked_package_data).dist_name,
                         meta_record)


class RemovePrivateEnvMetaAction(UnlinkPathAction):
    def __init__(self, transaction_context, linked_package_data, target_prefix):
        target_short_path = "conda-meta/private_envs"
        super(RemovePrivateEnvMetaAction, self).__init__(transaction_context, linked_package_data,
                                                         target_prefix, target_short_path)

    def execute(self):
        log.trace("removing private env '%s' from %s", self.linked_package_data.name,
                  self.target_full_path)
        remove_private_envs_meta(self.linked_package_data.name)

    def reverse(self):
        log.trace("adding back private env '%s' from %s", self.linked_package_data.name,
                  self.target_full_path)
        name = "%s-%s" % (self.package_info.repodata_record.name,
                          self.package_info.repodata_record.version)
        create_private_envs_meta(name, context.root_prefix, self.target_prefix)


# ######################################################
#  Fetch / Extract Actions
# ######################################################


class CacheUrlAction(PathAction):

    def __init__(self, url, target_pkgs_dir, target_package_basename, md5sum=None):
        self.url = url
        self.target_pkgs_dir = target_pkgs_dir
        self.target_package_basename = target_package_basename
        self.md5sum = md5sum
        self.hold_path = self.target_full_path + '.c~'

    def verify(self):
        assert '::' not in self.url
        self._verified = True

    def execute(self):
        # I hate inline imports, but I guess it's ok since we're importing from the conda.core
        # The alternative is passing the PackageCache class to CacheUrlAction __init__
        from .package_cache import PackageCache
        target_package_cache = PackageCache(self.target_pkgs_dir)

        log.trace("caching url %s => %s", self.url, self.target_full_path)

        if exists(self.hold_path):
            rm_rf(self.hold_path)

        if exists(self.target_full_path):
            if self.url.startswith('file:/') and self.url == path_to_url(self.target_full_path):
                # the source and destination are the same file, so we're done
                return
            else:
                backoff_rename(self.target_full_path, self.hold_path)

        if self.url.startswith('file:/'):
            source_path = url_to_path(self.url)
            if dirname(source_path) in context.pkgs_dirs:
                # if url points to another package cache, link to the writable cache
                create_hard_link_or_copy(source_path, self.target_full_path)
                source_package_cache = PackageCache(dirname(source_path))

                # the package is already in a cache, so it came from a remote url somewhere;
                #   make sure that remote url is the most recent url in the
                #   writable cache urls.txt
                origin_url = source_package_cache.urls_data.get_url(self.target_package_basename)
                if origin_url and Dist(origin_url).is_channel:
                    target_package_cache.urls_data.add_url(origin_url)
            else:
                # so our tarball source isn't a package cache, but that doesn't mean it's not
                #   in another package cache somewhere
                # let's try to find the actual, remote source url by matching md5sums, and then
                #   record that url as the remote source url in urls.txt
                # we do the search part of this operation before the create_link so that we
                #   don't md5sum-match the file created by 'create_link'
                source_md5sum = compute_md5sum(source_path)
                pc_entry = PackageCache.tarball_file_in_cache(source_path, source_md5sum)
                origin_url = pc_entry.get_urls_txt_value() if pc_entry else None

                # copy the tarball to the writable cache
                create_link(source_path, self.target_full_path, link_type=LinkType.copy,
                            force=context.force)

                if origin_url and Dist(origin_url).is_channel:
                    target_package_cache.urls_data.add_url(origin_url)
                else:
                    target_package_cache.urls_data.add_url(self.url)

        else:
            download(self.url, self.target_full_path, self.md5sum)
            target_package_cache.urls_data.add_url(self.url)

    def reverse(self):
        if exists(self.hold_path):
            log.trace("moving %s => %s", self.hold_path, self.target_full_path)
            rm_rf(self.target_full_path)
            backoff_rename(self.hold_path, self.target_full_path)

    def cleanup(self):
        rm_rf(self.hold_path)

    @property
    def target_full_path(self):
        return join(self.target_pkgs_dir, self.target_package_basename)


class ExtractPackageAction(PathAction):

    def __init__(self, source_full_path, target_pkgs_dir, target_extracted_package_dir):
        self.source_full_path = source_full_path
        self.target_pkgs_dir = target_pkgs_dir
        self.target_extracted_package_dir = target_extracted_package_dir
        self.hold_path = self.target_full_path + '.c~'

    def verify(self):
        self._verified = True

    def execute(self):
        # I hate inline imports, but I guess it's ok since we're importing from the conda.core
        # The alternative is passing the the classes to ExtractPackageAction __init__
        from .package_cache import PackageCache, PackageCacheEntry
        log.trace("extracting %s => %s", self.source_full_path, self.target_full_path)

        if exists(self.hold_path):
            rm_rf(self.hold_path)
        if exists(self.target_full_path):
            backoff_rename(self.target_full_path, self.hold_path)
        extract_tarball(self.source_full_path, self.target_full_path)

        target_package_cache = PackageCache(self.target_pkgs_dir)

        recorded_url = target_package_cache.urls_data.get_url(self.source_full_path)
        dist = Dist(recorded_url) if recorded_url else Dist(path_to_url(self.source_full_path))
        package_cache_entry = PackageCacheEntry.make_legacy(self.target_pkgs_dir, dist)
        target_package_cache[package_cache_entry.dist] = package_cache_entry

    def reverse(self):
        if exists(self.hold_path):
            log.trace("moving %s => %s", self.hold_path, self.target_full_path)
            rm_rf(self.target_full_path)
            backoff_rename(self.hold_path, self.target_full_path)

    def cleanup(self):
        rm_rf(self.hold_path)

    @property
    def target_full_path(self):
        return self.target_extracted_package_dir
