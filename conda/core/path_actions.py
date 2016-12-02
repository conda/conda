# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from abc import ABCMeta, abstractmethod
from logging import getLogger
from os.path import isfile, islink, join

from .._vendor.auxlib.compat import with_metaclass
from .._vendor.auxlib.ish import dals
from ..base.constants import LinkType
from ..common.path import get_python_path, win_path_ok
from ..core.linked_data import delete_linked_data, load_linked_data
from ..exceptions import CondaVerificationError, PaddingError
from ..gateways.disk.create import (compile_pyc, create_link, create_unix_entry_point,
                                    create_windows_entry_point_py, make_menu,
                                    write_conda_meta_record)
from ..gateways.disk.delete import maybe_rmdir_if_empty, rm_rf
from ..gateways.disk.read import exists
from ..gateways.disk.update import _PaddingError, rename, update_prefix
from ..models.dist import Dist
from ..models.record import Record
from ..utils import on_win

log = getLogger(__name__)


@with_metaclass(ABCMeta)
class PathAction(object):

    def __init__(self, transaction_context, target_prefix, target_short_path):
        self.transaction_context = transaction_context
        self.target_prefix = target_prefix
        self.target_short_path = target_short_path

    @property
    def target_full_path(self):
        trgt, shrt_pth = self.target_prefix, self.target_short_path
        return join(trgt, win_path_ok(shrt_pth)) if trgt and shrt_pth else None

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

    def __repr__(self):
        attrs = ('source_prefix', 'source_short_path', 'target_prefix', 'target_short_path',
                 'link_type', 'prefix_placeholder', 'file_mode')
        args = ('%s=%s' % (attr, getattr(self, attr, None))
                for attr in attrs if hasattr(self, attr))
        return "%s(%s)" % (self.__class__.__name__, ', '.join(args))


# ######################################################
#  Creation Actions
# ######################################################

@with_metaclass(ABCMeta)
class CreatePathAction(PathAction):
    # All CreatePathAction subclasses must create a SINGLE new path
    #   the short/in-prefix version of that path must be returned by execute()

    def __init__(self, transaction_context, package_info, source_prefix, source_short_path,
                 target_prefix, target_short_path):
        super(CreatePathAction, self).__init__(transaction_context,
                                               target_prefix, target_short_path)
        self.package_info = package_info
        self.source_prefix = source_prefix
        self.source_short_path = source_short_path

    def cleanup(self):
        # create actions typically won't need cleanup
        pass

    @property
    def source_full_path(self):
        prfx, shrt_pth = self.source_prefix, self.source_short_path
        return join(prfx, win_path_ok(shrt_pth)) if prfx and shrt_pth else None


class LinkPathAction(CreatePathAction):

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

    def execute(self):
        log.debug("linking %s => %s", self.source_full_path, self.target_full_path)
        create_link(self.source_full_path, self.target_full_path, self.link_type)

    def reverse(self):
        if self.link_type == LinkType.directory:
            maybe_rmdir_if_empty(self.target_full_path)
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

    def execute(self):
        super(PrefixReplaceLinkAction, self).execute()
        if islink(self.source_full_path):
            log.info("Ignoring prefix update for symlink with source path %s",
                     self.source_full_path)
            return

        try:
            log.debug("rewriting prefixes in %s", self.target_full_path)
            update_prefix(self.target_full_path, self.target_prefix, self.prefix_placeholder,
                          self.file_mode)
        except _PaddingError:
            raise PaddingError(self.target_full_path, self.prefix_placeholder,
                               len(self.prefix_placeholder))


class MakeMenuAction(CreatePathAction):

    def __init__(self, transaction_context, package_info,
                 target_prefix, target_short_path):
        super(MakeMenuAction, self).__init__(transaction_context, package_info,
                                             None, None, target_prefix, target_short_path)

    def verify(self):
        pass

    def execute(self):
        log.debug("making menu for %s", self.target_full_path)
        make_menu(self.target_prefix, self.target_short_path, remove=False)

    def reverse(self):
        log.debug("removing menu for %s", self.target_full_path)
        make_menu(self.target_prefix, self.target_short_path, remove=True)


class CompilePycAction(CreatePathAction):

    def __init__(self, transaction_context, package_info, target_prefix,
                 source_short_path, target_short_path):
        super(CompilePycAction, self).__init__(transaction_context, package_info,
                                               target_prefix, source_short_path,
                                               target_prefix, target_short_path)

    def verify(self):
        pass

    def execute(self):
        log.debug("compiling %s", self.target_full_path)
        python_short_path = get_python_path(self.transaction_context['target_python_version'])
        python_full_path = join(self.target_prefix, win_path_ok(python_short_path))
        compile_pyc(python_full_path, self.source_full_path)

    def reverse(self):
        rm_rf(self.target_full_path)


class CreatePythonEntryPointAction(CreatePathAction):

    def __init__(self, transaction_context, package_info, target_prefix, target_short_path,
                 module, func):
        super(CreatePythonEntryPointAction, self).__init__(transaction_context, package_info,
                                                           None, None,
                                                           target_prefix, target_short_path)
        self.module = module
        self.func = func

    def verify(self):
        pass

    def execute(self):
        log.debug("creating entry point %s", self.target_full_path)
        if on_win:
            create_windows_entry_point_py(self.target_full_path, self.module, self.func)
        else:
            python_short_path = get_python_path(self.transaction_context['target_python_version'])
            python_full_path = join(self.target_prefix, win_path_ok(python_short_path))
            create_unix_entry_point(self.target_full_path, python_full_path,
                                    self.module, self.func)

    def reverse(self):
        rm_rf(self.target_full_path)


class CreateCondaMetaAction(CreatePathAction):

    def __init__(self, transaction_context, package_info, target_prefix, meta_record):
        target_short_path = 'conda-meta/' + package_info.repodata_record.fn
        super(CreateCondaMetaAction, self).__init__(transaction_context, package_info,
                                                    None, None, target_prefix, target_short_path)
        self.meta_record = meta_record

    def verify(self):
        pass

    def execute(self):
        log.debug("creating conda-meta %s", self.target_full_path)
        write_conda_meta_record(self.target_prefix, self.meta_record)
        load_linked_data(self.target_prefix, Dist(self.package_info.repodata_record).dist_name,
                         self.meta_record)

    def reverse(self):
        delete_linked_data(self.target_prefix, Dist(self.package_info.repodata_record),
                           delete=False)
        rm_rf(self.target_full_path)


# ######################################################
#  Removal Actions
# ######################################################

@with_metaclass(ABCMeta)
class RemovePathAction(PathAction):

    def __init__(self, transaction_context, linked_package_data, target_prefix, target_short_path):
        super(RemovePathAction, self).__init__(transaction_context,
                                               target_prefix, target_short_path)
        self.linked_package_data = linked_package_data

    def verify(self):
        # inability to remove will trigger a rollback
        # can't definitely know if path can be removed until it's attempted and failed
        pass


class UnlinkPathAction(RemovePathAction):
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
            log.debug("renaming %s => %s", self.target_short_path, self.holding_short_path)
            rename(self.target_full_path, self.holding_full_path)

    def reverse(self):
        if self.link_type != LinkType.directory and exists(self.holding_full_path):
            log.debug("reversing rename %s => %s", self.holding_short_path, self.target_short_path)
            rename(self.holding_full_path, self.target_full_path)

    def cleanup(self):
        if self.link_type == LinkType.directory:
            maybe_rmdir_if_empty(self.target_full_path)
        else:
            rm_rf(self.holding_full_path)


class RemoveMenuAction(RemovePathAction):

    def __init__(self, transaction_context, linked_package_data,
                 target_prefix, target_short_path):
        super(RemoveMenuAction, self).__init__(transaction_context, linked_package_data,
                                               target_prefix, target_short_path)

    def execute(self):
        log.debug("removing menu for %s ", self.target_prefix)
        make_menu(self.target_prefix, self.target_short_path, remove=False)

    def reverse(self):
        log.debug("re-creating menu for %s ", self.target_prefix)
        make_menu(self.target_prefix, self.target_short_path, remove=True)

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
        log.debug("reloading cache entry %s", self.target_full_path)
        load_linked_data(self.target_prefix,
                         Dist(self.linked_package_data).dist_name,
                         meta_record)
