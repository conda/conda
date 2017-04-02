# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from abc import ABCMeta, abstractmethod, abstractproperty
from errno import EXDEV
import json
from logging import getLogger
from os.path import dirname, join
import re

from .linked_data import delete_linked_data, get_python_version_for_prefix, load_linked_data
from .portability import _PaddingError, update_prefix
from .._vendor.auxlib.compat import with_metaclass
from .._vendor.auxlib.ish import dals
from ..base.context import context
from ..common.compat import iteritems, on_win
from ..common.path import (get_bin_directory_short_path, get_leaf_directories,
                           get_python_noarch_target_path, get_python_short_path,
                           parse_entry_point_def, preferred_env_to_prefix, pyc_path, url_to_path,
                           win_path_ok)
from ..common.url import path_to_url
from ..exceptions import CondaUpgradeError, CondaVerificationError, PaddingError
from ..gateways.disk.create import (compile_pyc, create_hard_link_or_copy, create_link,
                                    create_private_envs_meta, create_private_pkg_entry_point,
                                    create_unix_python_entry_point,
                                    create_windows_python_entry_point, extract_tarball,
                                    make_menu, write_linked_package_record)
from ..gateways.disk.delete import remove_private_envs_meta, rm_rf, try_rmdir_all_empty
from ..gateways.disk.read import compute_md5sum, isfile, islink, lexists
from ..gateways.disk.update import backoff_rename, touch
from ..gateways.download import download
from ..models.dist import Dist
from ..models.enums import LinkType, NoarchType, PathType
from ..models.index_record import IndexRecord, Link

try:
    from cytoolz.itertoolz import concatv
except ImportError:
    from .._vendor.toolz.itertoolz import concatv  # NOQA

log = getLogger(__name__)


REPR_IGNORE_KWARGS = (
    'transaction_context',
    'package_info',
    'hold_path',
)

@with_metaclass(ABCMeta)
class PathAction(object):

    _verified = False

    @abstractmethod
    def verify(self):
        # if verify fails, it should return an exception object rather than raise
        #  at the end of a verification run, all errors will be raised as a CondaMultiError
        # after successful verification, the verify method should set self._verified = True
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
        if trgt is not None and shrt_pth is not None:
            return join(trgt, win_path_ok(shrt_pth))
        else:
            return None


# ######################################################
#  Creation of Paths within a Prefix
# ######################################################

@with_metaclass(ABCMeta)
class CreateInPrefixPathAction(PrefixPathAction):
    # All CreatePathAction subclasses must create a SINGLE new path
    #   the short/in-prefix version of that path must be returned by execute()

    def __init__(self, transaction_context, package_info, source_prefix, source_short_path,
                 target_prefix, target_short_path):
        super(CreateInPrefixPathAction, self).__init__(transaction_context,
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


class LinkPathAction(CreateInPrefixPathAction):

    @classmethod
    def create_file_link_actions(cls, transaction_context, package_info, target_prefix,
                                 requested_link_type):
        def make_file_link_action(source_path_info):
            # TODO: this inner function is still kind of a mess
            noarch = package_info.index_json_record.noarch
            if noarch == NoarchType.python:
                sp_dir = transaction_context['target_site_packages_short_path']
                target_short_path = get_python_noarch_target_path(source_path_info.path, sp_dir)
            elif noarch is None or noarch == NoarchType.generic:
                target_short_path = source_path_info.path
            else:
                raise CondaUpgradeError(dals("""
                The current version of conda is too old to install this package.
                Please update conda."""))

            def get_prefix_replace(path_info, requested_link_type):
                if path_info.prefix_placeholder:
                    link_type = LinkType.copy
                    prefix_placehoder = path_info.prefix_placeholder
                    file_mode = path_info.file_mode
                elif path_info.no_link or path_info.path_type == PathType.softlink:
                    link_type = LinkType.copy
                    prefix_placehoder, file_mode = '', None
                else:
                    link_type = requested_link_type
                    prefix_placehoder, file_mode = '', None

                return link_type, prefix_placehoder, file_mode

            link_type, placeholder, fmode = get_prefix_replace(source_path_info,
                                                               requested_link_type)

            if placeholder:
                return PrefixReplaceLinkAction(transaction_context, package_info,
                                               package_info.extracted_package_dir,
                                               source_path_info.path,
                                               target_prefix, target_short_path,
                                               placeholder, fmode)
            else:
                return LinkPathAction(transaction_context, package_info,
                                      package_info.extracted_package_dir, source_path_info.path,
                                      target_prefix, target_short_path, link_type)
        return tuple(make_file_link_action(spi) for spi in package_info.paths_data.paths)

    @classmethod
    def create_directory_actions(cls, transaction_context, package_info, target_prefix,
                                 requested_link_type, file_link_actions):
        leaf_directories = get_leaf_directories(axn.target_short_path for axn in file_link_actions)
        return tuple(
            cls(transaction_context, package_info, None, None,
                target_prefix, directory_short_path, LinkType.directory)
            for directory_short_path in leaf_directories
        )

    @classmethod
    def create_python_entry_point_windows_exe_action(cls, transaction_context, package_info,
                                                     target_prefix, requested_link_type,
                                                     entry_point_def):
        source_directory = context.conda_prefix
        source_short_path = 'Scripts/conda.exe'
        command, _, _ = parse_entry_point_def(entry_point_def)
        target_short_path = "Scripts/%s.exe" % command
        return cls(transaction_context, package_info, source_directory,
                   source_short_path, target_prefix, target_short_path,
                   requested_link_type)

    def __init__(self, transaction_context, package_info,
                 extracted_package_dir, source_short_path,
                 target_prefix, target_short_path, link_type):
        super(LinkPathAction, self).__init__(transaction_context, package_info,
                                             extracted_package_dir, source_short_path,
                                             target_prefix, target_short_path)
        self.link_type = link_type
        self._execute_successful = False

    def verify(self):
        # TODO: consider checking hashsums
        if self.link_type != LinkType.directory and not lexists(self.source_full_path):
            return CondaVerificationError(dals("""
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
        self._execute_successful = True

    def reverse(self):
        if self._execute_successful:
            log.trace("reversing link creation %s", self.target_prefix)
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
            return CondaVerificationError(dals("""
            The package for %s located at %s
            appears to be corrupted. For the file at path %s
            a prefix_placeholder and file_mode must be specified. Instead got values
            of '%s' and '%s'.
            """ % (self.package_info.index_json_record.name,
                   self.package_info.extracted_package_dir,
                   self.source_short_path, self.prefix_placeholder, self.file_mode)))
        if not isfile(self.source_full_path):
            return CondaVerificationError(dals("""
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


class MakeMenuAction(CreateInPrefixPathAction):

    @classmethod
    def create_actions(cls, transaction_context, package_info, target_prefix, requested_link_type):
        if on_win and context.shortcuts:
            MENU_RE = re.compile(r'^menu/.*\.json$', re.IGNORECASE)
            return tuple(cls(transaction_context, package_info, target_prefix, spi.path)
                         for spi in package_info.paths_data.paths if bool(MENU_RE.match(spi.path)))
        else:
            return ()

    def __init__(self, transaction_context, package_info, target_prefix, target_short_path):
        super(MakeMenuAction, self).__init__(transaction_context, package_info,
                                             None, None, target_prefix, target_short_path)
        self._execute_successful = False

    def execute(self):
        log.trace("making menu for %s", self.target_full_path)
        make_menu(self.target_prefix, self.target_short_path, remove=False)
        self._execute_successful = True

    def reverse(self):
        if self._execute_successful:
            log.trace("removing menu for %s", self.target_full_path)
            make_menu(self.target_prefix, self.target_short_path, remove=True)


class CreateNonadminAction(CreateInPrefixPathAction):

    @classmethod
    def create_actions(cls, transaction_context, package_info, target_prefix, requested_link_type):
        if on_win and lexists(join(context.root_prefix, '.nonadmin')):
            return cls(transaction_context, package_info, target_prefix),
        else:
            return ()

    def __init__(self, transaction_context, package_info, target_prefix):
        super(CreateNonadminAction, self).__init__(transaction_context, package_info, None, None,
                                                   target_prefix, '.nonadmin')

    def execute(self):
        log.trace("touching nonadmin %s", self.target_full_path)
        self._file_created = touch(self.target_full_path)

    def reverse(self):
        if self._file_created:
            log.trace("removing nonadmin file %s", self.target_full_path)
            rm_rf(self.target_full_path)


class CompilePycAction(CreateInPrefixPathAction):

    @classmethod
    def create_actions(cls, transaction_context, package_info, target_prefix, requested_link_type,
                       file_link_actions):
        noarch = package_info.package_metadata and package_info.package_metadata.noarch
        if noarch is not None and noarch.type == NoarchType.python:
            noarch_py_file_re = re.compile(r'^site-packages[/\\][^\t\n\r\f\v]+\.py$')
            py_ver = transaction_context['target_python_version']
            py_files = (axn.target_short_path for axn in file_link_actions
                        if noarch_py_file_re.match(axn.source_short_path))
            return tuple(cls(transaction_context, package_info, target_prefix,
                             pf, pyc_path(pf, py_ver))
                         for pf in py_files)
        else:
            return ()

    def __init__(self, transaction_context, package_info, target_prefix,
                 source_short_path, target_short_path):
        super(CompilePycAction, self).__init__(transaction_context, package_info,
                                               target_prefix, source_short_path,
                                               target_prefix, target_short_path)
        self._execute_successful = False

    def execute(self):
        # compile_pyc is sometimes expected to fail, for example a python 3.6 file
        #   installed into a python 2 environment, but no code paths actually importing it
        # technically then, this file should be removed from the manifest in conda-meta, but
        #   at the time of this writing that's not currently happening
        log.trace("compiling %s", self.target_full_path)
        target_python_version = self.transaction_context['target_python_version']
        python_short_path = get_python_short_path(target_python_version)
        python_full_path = join(self.target_prefix, win_path_ok(python_short_path))
        compile_pyc(python_full_path, self.source_full_path, self.target_full_path)
        self._execute_successful = True

    def reverse(self):
        if self._execute_successful:
            log.trace("reversing pyc creation %s", self.target_full_path)
            rm_rf(self.target_full_path)


class CreatePythonEntryPointAction(CreateInPrefixPathAction):

    @classmethod
    def create_actions(cls, transaction_context, package_info, target_prefix, requested_link_type):
        noarch = package_info.package_metadata and package_info.package_metadata.noarch
        if noarch is not None and noarch.type == NoarchType.python:
            def this_triplet(entry_point_def):
                command, module, func = parse_entry_point_def(entry_point_def)
                target_short_path = "%s/%s" % (get_bin_directory_short_path(), command)
                if on_win:
                    target_short_path += "-script.py"
                return target_short_path, module, func

            actions = tuple(cls(transaction_context, package_info, target_prefix,
                                *this_triplet(ep_def))
                            for ep_def in noarch.entry_points or ())

            if on_win:  # pragma: unix no cover
                actions += tuple(
                    LinkPathAction.create_python_entry_point_windows_exe_action(
                        transaction_context, package_info, target_prefix,
                        requested_link_type, ep_def
                    ) for ep_def in noarch.entry_points or ()
                )

            return actions
        else:
            return ()

    def __init__(self, transaction_context, package_info, target_prefix, target_short_path,
                 module, func):
        super(CreatePythonEntryPointAction, self).__init__(transaction_context, package_info,
                                                           None, None,
                                                           target_prefix, target_short_path)
        self.module = module
        self.func = func
        self._execute_successful = False

    def execute(self):
        log.trace("creating python entry point %s", self.target_full_path)
        if on_win:
            create_windows_python_entry_point(self.target_full_path, self.module, self.func)
        else:
            target_python_version = self.transaction_context['target_python_version']
            python_short_path = get_python_short_path(target_python_version)
            python_full_path = join(self.target_prefix, win_path_ok(python_short_path))
            create_unix_python_entry_point(self.target_full_path, python_full_path,
                                           self.module, self.func)
        self._execute_successful = True

    def reverse(self):
        if self._execute_successful:
            log.trace("reversing python entry point creation %s", self.target_full_path)
            rm_rf(self.target_full_path)


class CreateApplicationEntryPointAction(CreateInPrefixPathAction):

    @classmethod
    def create_actions(cls, transaction_context, package_info, target_prefix, requested_link_type):
        if target_prefix == package_info.repodata_record.preferred_env != context.root_prefix:
            def package_executable_short_paths():
                exe_paths = (package_info.package_metadata
                             and package_info.package_metadata.preferred_env
                             and package_info.package_metadata.preferred_env.executable_paths
                             or ())
                for axn in exe_paths:
                    yield axn.target_short_path

            private_env_prefix = preferred_env_to_prefix(
                package_info.repodata_record.preferred_env,
                context.root_prefix, context.envs_dirs
            )
            assert private_env_prefix == target_prefix, (private_env_prefix, target_prefix)

            # target_prefix here is not the same as target_prefix for the larger transaction
            return tuple(
                cls(transaction_context, package_info, private_env_prefix, executable_short_path,
                    context.root_prefix, executable_short_path)
                for executable_short_path in package_executable_short_paths()
            )
        else:
            return ()

    def __init__(self, transaction_context, package_info, source_prefix, source_short_path,
                 target_prefix, target_short_path):
        super(CreateApplicationEntryPointAction, self).__init__(transaction_context, package_info,
                                                                source_prefix, source_short_path,
                                                                target_prefix, target_short_path)
        self._execute_successful = False

    def execute(self):
        log.trace("creating application entry point %s => %s",
                  self.source_full_path, self.target_full_path)
        if self.source_prefix == context.conda_prefix:
            # this could blow up for the special case of application entry points in conda's
            #   private environment
            # in that case, probably should use the python version from transaction_context
            conda_python_version = self.transaction_context['target_python_version']
        else:
            conda_python_version = get_python_version_for_prefix(context.conda_prefix)
        conda_python_short_path = get_python_short_path(conda_python_version)
        conda_python_full_path = join(context.conda_prefix, win_path_ok(conda_python_short_path))
        create_private_pkg_entry_point(self.source_full_path, self.target_full_path,
                                       conda_python_full_path)
        self._execute_successful = True

    def reverse(self):
        if self._execute_successful:
            log.trace("reversing application entry point creation %s", self.target_full_path)
            rm_rf(self.target_full_path)


class CreateLinkedPackageRecordAction(CreateInPrefixPathAction):
    # this is the action that creates a packages json file in the conda-meta/ directory

    @classmethod
    def create_actions(cls, transaction_context, package_info, target_prefix, requested_link_type,
                       all_target_short_paths):
        # 'all_target_short_paths' is especially significant here, because it is the record
        #   of the paths that will be removed when the package is unlinked

        link = Link(source=package_info.extracted_package_dir, type=requested_link_type)
        linked_package_record = IndexRecord.from_objects(package_info.repodata_record,
                                                         package_info.index_json_record,
                                                         files=all_target_short_paths,
                                                         link=link,
                                                         url=package_info.url)

        target_short_path = 'conda-meta/' + Dist(package_info).to_filename('.json')
        return cls(transaction_context, package_info, target_prefix, target_short_path,
                   linked_package_record),

    def __init__(self, transaction_context, package_info, target_prefix, target_short_path,
                 linked_package_record):
        super(CreateLinkedPackageRecordAction, self).__init__(transaction_context, package_info,
                                                              None, None, target_prefix,
                                                              target_short_path)
        self.linked_package_record = linked_package_record
        self._linked_data_loaded = False

    def execute(self):
        log.trace("creating linked package record %s", self.target_full_path)
        write_linked_package_record(self.target_prefix, self.linked_package_record)
        load_linked_data(self.target_prefix, Dist(self.package_info.repodata_record).dist_name,
                         self.linked_package_record)
        self._linked_data_loaded = True

    def reverse(self):
        log.trace("reversing linked package record creation %s", self.target_full_path)
        if self._linked_data_loaded:
            delete_linked_data(self.target_prefix, Dist(self.package_info.repodata_record),
                               delete=False)
        rm_rf(self.target_full_path)


class CreatePrivateEnvMetaAction(CreateInPrefixPathAction):

    @classmethod
    def create_actions(cls, transaction_context, package_info, target_prefix, requested_link_type):
        if target_prefix == package_info.repodata_record.preferred_env != context.root_prefix:
            return cls(transaction_context, package_info, target_prefix),
        else:
            return ()

    def __init__(self, transaction_context, package_info, private_env_prefix):
        # source is the private env (which is the target of the overall transaction)
        # the target of this action is context.root_prefix/conda-meta/private_envs
        source_prefix = private_env_prefix
        target_short_path = 'conda-meta/private_envs'
        self.private_env_prefix = private_env_prefix
        super(CreatePrivateEnvMetaAction, self).__init__(transaction_context, package_info,
                                                         source_prefix, None,
                                                         context.root_prefix, target_short_path)
        self._execute_successful = False

    def execute(self):
        log.trace("creating private env entry for '%s' in %s",
                  self.package_info.repodata_record.name, self.target_full_path)
        # TODO: need to capture old env entry if it was there, so that it can be reversed
        name = "%s-%s" % (self.package_info.repodata_record.name,
                          self.package_info.repodata_record.version)
        create_private_envs_meta(name, context.root_prefix, self.target_prefix)
        self._execute_successful = True

    def reverse(self):
        if self._execute_successful:
            log.trace("reversing private env entry for '%s' in %s",
                      self.package_info.repodata_record.name, self.target_full_path)
            remove_private_envs_meta(self.package_info.repodata_record.name)


# ######################################################
#  Removal of Paths within a Prefix
# ######################################################

@with_metaclass(ABCMeta)
class RemoveFromPrefixPathAction(PrefixPathAction):

    def __init__(self, transaction_context, linked_package_data, target_prefix, target_short_path):
        super(RemoveFromPrefixPathAction, self).__init__(transaction_context,
                                                         target_prefix, target_short_path)
        self.linked_package_data = linked_package_data

    def verify(self):
        # inability to remove will trigger a rollback
        # can't definitely know if path can be removed until it's attempted and failed
        self._verified = True


class UnlinkPathAction(RemoveFromPrefixPathAction):
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
            backoff_rename(self.target_full_path, self.holding_full_path, force=True)

    def reverse(self):
        if self.link_type != LinkType.directory and lexists(self.holding_full_path):
            log.trace("reversing rename %s => %s", self.holding_short_path, self.target_short_path)
            backoff_rename(self.holding_full_path, self.target_full_path, force=True)

    def cleanup(self):
        if self.link_type == LinkType.directory:
            try_rmdir_all_empty(self.target_full_path)
        else:
            rm_rf(self.holding_full_path)


class RemoveMenuAction(RemoveFromPrefixPathAction):

    @classmethod
    def create_actions(cls, transaction_context, linked_package_data, target_prefix):
        if on_win:
            MENU_RE = re.compile(r'^menu/.*\.json$', re.IGNORECASE)
            return tuple(cls(transaction_context, linked_package_data, target_prefix, trgt)
                         for trgt in linked_package_data.files if bool(MENU_RE.match(trgt)))
        else:
            return ()

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


class RemoveLinkedPackageRecordAction(UnlinkPathAction):

    def __init__(self, transaction_context, linked_package_data, target_prefix, target_short_path):
        super(RemoveLinkedPackageRecordAction, self).__init__(transaction_context,
                                                              linked_package_data,
                                                              target_prefix, target_short_path)

    def execute(self):
        super(RemoveLinkedPackageRecordAction, self).execute()
        delete_linked_data(self.target_prefix, Dist(self.linked_package_data),
                           delete=False)

    def reverse(self):
        super(RemoveLinkedPackageRecordAction, self).reverse()
        with open(self.target_full_path, 'r') as fh:
            meta_record = IndexRecord(**json.loads(fh.read()))
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
        log.trace("adding back private env '%s' to %s", self.linked_package_data.name,
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

        if lexists(self.hold_path):
            rm_rf(self.hold_path)

        if lexists(self.target_full_path):
            if self.url.startswith('file:/') and self.url == path_to_url(self.target_full_path):
                # the source and destination are the same file, so we're done
                return
            else:
                backoff_rename(self.target_full_path, self.hold_path, force=True)

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
        if lexists(self.hold_path):
            log.trace("moving %s => %s", self.hold_path, self.target_full_path)
            backoff_rename(self.hold_path, self.target_full_path, force=True)

    def cleanup(self):
        rm_rf(self.hold_path)

    @property
    def target_full_path(self):
        return join(self.target_pkgs_dir, self.target_package_basename)

    def __str__(self):
        return 'CacheUrlAction<url=%r, target_full_path=%r>' % (self.url, self.target_full_path)


class ExtractPackageAction(PathAction):

    def __init__(self, source_full_path, target_pkgs_dir, target_extracted_dirname):
        self.source_full_path = source_full_path
        self.target_pkgs_dir = target_pkgs_dir
        self.target_extracted_dirname = target_extracted_dirname
        self.hold_path = self.target_full_path + '.c~'

    def verify(self):
        self._verified = True

    def execute(self):
        # I hate inline imports, but I guess it's ok since we're importing from the conda.core
        # The alternative is passing the the classes to ExtractPackageAction __init__
        from .package_cache import PackageCache, PackageCacheEntry
        log.trace("extracting %s => %s", self.source_full_path, self.target_full_path)

        if lexists(self.hold_path):
            rm_rf(self.hold_path)
        if lexists(self.target_full_path):
            try:
                backoff_rename(self.target_full_path, self.hold_path)
            except (IOError, OSError) as e:
                if e.errno == EXDEV:
                    # OSError(18, 'Invalid cross-device link')
                    # https://github.com/docker/docker/issues/25409
                    # ignore, but we won't be able to roll back
                    log.debug("Invalid cross-device link on rename %s => %s",
                              self.target_full_path, self.hold_path)
                    rm_rf(self.target_full_path)
                else:
                    raise
        extract_tarball(self.source_full_path, self.target_full_path)

        target_package_cache = PackageCache(self.target_pkgs_dir)

        recorded_url = target_package_cache.urls_data.get_url(self.source_full_path)
        dist = Dist(recorded_url) if recorded_url else Dist(path_to_url(self.source_full_path))
        package_cache_entry = PackageCacheEntry.make_legacy(self.target_pkgs_dir, dist)
        target_package_cache[package_cache_entry.dist] = package_cache_entry

    def reverse(self):
        rm_rf(self.target_full_path)
        if lexists(self.hold_path):
            log.trace("moving %s => %s", self.hold_path, self.target_full_path)
            rm_rf(self.target_full_path)
            backoff_rename(self.hold_path, self.target_full_path)

    def cleanup(self):
        rm_rf(self.hold_path)

    @property
    def target_full_path(self):
        return join(self.target_pkgs_dir, self.target_extracted_dirname)

    def __str__(self):
        return ('ExtractPackageAction<source_full_path=%r, target_full_path=%r>'
                % (self.source_full_path, self.target_full_path))
