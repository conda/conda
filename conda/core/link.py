# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
import warnings
from logging import getLogger
from os.path import join
from subprocess import CalledProcessError, check_call
from traceback import format_exc

from .linked_data import (get_python_version_for_prefix, linked_data as get_linked_data,
                          load_meta)
from .package_cache import PackageCache
from .path_actions import (CompilePycAction, CreateApplicationEntryPointAction,
                           CreateLinkedPackageRecordAction, CreatePrivateEnvMetaAction,
                           CreatePythonEntryPointAction, LinkPathAction, MakeMenuAction,
                           RemoveLinkedPackageRecordAction, RemoveMenuAction,
                           RemovePrivateEnvMetaAction, UnlinkPathAction)
from .._vendor.auxlib.ish import dals
from ..base.context import context
from ..common.compat import on_win, text_type
from ..common.path import (explode_directories, get_all_directories, get_bin_directory_short_path,
                           get_major_minor_version,
                           get_python_site_packages_short_path)
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.read import collect_all_info_for_package, isfile
from ..gateways.disk.test import hardlink_supported, softlink_supported
from ..models.dist import Dist
from ..models.enums import LinkType

try:
    from cytoolz.itertoolz import concat, concatv
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv  # NOQA

log = getLogger(__name__)


def determine_link_type(extracted_package_dir, target_prefix):
    source_test_file = join(extracted_package_dir, 'info', 'index.json')
    if context.always_copy:
        return LinkType.copy
    if context.always_softlink:
        return LinkType.softlink
    if hardlink_supported(source_test_file, target_prefix):
        return LinkType.hardlink
    if context.allow_softlinks and softlink_supported(source_test_file, target_prefix):
        return LinkType.softlink
    return LinkType.copy



def make_unlink_actions(transaction_context, target_prefix, linked_package_data):
    # no side effects in this function!
    unlink_path_actions = tuple(UnlinkPathAction(transaction_context, linked_package_data,
                                                 target_prefix, trgt)
                                for trgt in linked_package_data.files)

    remove_menu_actions = RemoveMenuAction.create_actions(transaction_context,
                                                          linked_package_data,
                                                          target_prefix)

    meta_short_path = '%s/%s' % ('conda-meta', Dist(linked_package_data).to_filename('.json'))
    remove_conda_meta_actions = (RemoveLinkedPackageRecordAction(transaction_context,
                                                                 linked_package_data,
                                                                 target_prefix, meta_short_path),)

    _all_d = get_all_directories(axn.target_short_path for axn in unlink_path_actions)
    all_directories = sorted(explode_directories(_all_d, already_split=True), reverse=True)
    directory_remove_actions = tuple(UnlinkPathAction(transaction_context, linked_package_data,
                                                      target_prefix, d, LinkType.directory)
                                     for d in all_directories)

    if linked_package_data.preferred_env is not None:
        app_entry_point_short_path = os.path.join(get_bin_directory_short_path(),
                                                  linked_package_data.name)
        unlink_app_entry_point = UnlinkPathAction(transaction_context, linked_package_data,
                                                  context.root_prefix, app_entry_point_short_path),
        unlink_path_actions = unlink_path_actions + unlink_app_entry_point
        private_envs_meta_action = RemovePrivateEnvMetaAction(
            transaction_context, linked_package_data, target_prefix),
    else:
        private_envs_meta_action = ()

    return tuple(concatv(
        remove_conda_meta_actions,
        remove_menu_actions,
        unlink_path_actions,
        directory_remove_actions,
        private_envs_meta_action,
    ))


class UnlinkLinkTransaction(object):

    @classmethod
    def create_from_dists(cls, index, target_prefix, unlink_dists, link_dists):
        # This constructor method helps to patch into the 'plan' framework
        linked_packages_data_to_unlink = tuple(load_meta(target_prefix, dist)
                                               for dist in unlink_dists)

        log.debug("instantiating UnlinkLinkTransaction with\n"
                  "  target_prefix: %s\n"
                  "  unlink_dists:\n"
                  "    %s\n"
                  "  link_dists:\n"
                  "    %s\n",
                  target_prefix,
                  '\n    '.join(text_type(d) for d in unlink_dists),
                  '\n    '.join(text_type(d) for d in link_dists))

        pkg_dirs_to_link = tuple(PackageCache[dist].extracted_package_dir for dist in link_dists)
        assert all(pkg_dirs_to_link)
        packages_info_to_link = tuple(collect_all_info_for_package(index[dist], pkg_dir)
                                      for dist, pkg_dir in zip(link_dists, pkg_dirs_to_link))

        return UnlinkLinkTransaction(target_prefix, linked_packages_data_to_unlink,
                                     packages_info_to_link)

    def __init__(self, target_prefix, linked_packages_data_to_unlink, packages_info_to_link):
        # type: (str, Sequence[Dist], Sequence[PackageInfo]) -> NoneType
        # order of unlink_dists and link_dists will be preserved throughout
        #   should be given in dependency-sorted order

        self.target_prefix = target_prefix
        self.linked_packages_data_to_unlink = linked_packages_data_to_unlink
        self.packages_info_to_link = packages_info_to_link

        self._prepared = False
        self._verified = False

    def prepare(self):
        if self._prepared:
            return

        # gather information from disk and caches
        self.prefix_linked_data = get_linked_data(self.target_prefix)
        link_types = tuple(determine_link_type(pkg_info.extracted_package_dir, self.target_prefix)
                           for pkg_info in self.packages_info_to_link)

        # make all the path actions
        # no side effects allowed when instantiating these action objects
        transaction_context = dict()
        python_version = self.get_python_version(self.target_prefix,
                                                 self.linked_packages_data_to_unlink,
                                                 self.packages_info_to_link)
        transaction_context['target_python_version'] = python_version
        sp = get_python_site_packages_short_path(python_version)
        transaction_context['target_site_packages_short_path'] = sp

        unlink_actions = tuple((lnkd_pkg_data, make_unlink_actions(transaction_context,
                                                                   self.target_prefix,
                                                                   lnkd_pkg_data))
                               for lnkd_pkg_data in self.linked_packages_data_to_unlink)
        link_actions = tuple((pkg_info, self.make_link_actions(transaction_context, pkg_info,
                                                               self.target_prefix, lt))
                             for pkg_info, lt in zip(self.packages_info_to_link, link_types))
        self.all_actions = tuple(per_pkg_actions for per_pkg_actions in
                                 concatv(unlink_actions, link_actions))
        self.num_unlink_pkgs = len(unlink_actions)

        self._prepared = True

    def verify(self):
        if not self._prepared:
            self.prepare()

        next((action.verify() for x in self.all_actions for action in x[1]), None)
        self._verified = True

    def execute(self):
        if not self._verified:
            self.verify()

        try:
            for pkg_idx, (pkg_data, actions) in enumerate(self.all_actions):
                for axn_idx, action in enumerate(actions):
                    action.execute()

        except:
            log.error("Something bad happened, but it's okay because I'm going to roll back now.")
            log.debug("Error in action %r", action)
            log.debug(format_exc())

            failed_pkg_idx, failed_axn_idx = pkg_idx, axn_idx
            reverse_actions = self.all_actions[:failed_pkg_idx+1]
            for pkg_idx, (pkg_data, actions) in reversed(tuple(enumerate(reverse_actions))):
                reverse_from_axn_idx = failed_axn_idx if pkg_idx == failed_pkg_idx else -1
                self._reverse_actions(self.target_prefix, self.num_unlink_pkgs,
                                      pkg_idx, pkg_data, actions, reverse_from_axn_idx)
            raise

        else:
            for pkg_idx, (pkg_data, actions) in enumerate(self.all_actions):
                for axn_idx, action in enumerate(actions):
                    action.cleanup()

    @staticmethod
    def _execute_actions(target_prefix, num_unlink_pkgs, pkg_idx, pkg_data, actions):
        axn_idx = 0
        try:
            dist = Dist(pkg_data)
            is_unlink = pkg_idx <= num_unlink_pkgs - 1
            if is_unlink:
                log.info("===> UNLINKING PACKAGE: %s <===\n"
                         "  prefix=%s\n",
                         dist, target_prefix)

            else:
                log.info("===> LINKING PACKAGE: %s <===\n"
                         "  prefix=%s\n"
                         "  source=%s\n",
                         dist, target_prefix, pkg_data.extracted_package_dir)

            run_script(target_prefix, Dist(pkg_data), 'pre-unlink' if is_unlink else 'pre-link')

            for axn_idx, action in enumerate(actions):
                action.execute()

            run_script(target_prefix, Dist(pkg_data), 'post-unlink' if is_unlink else 'post-link')
        finally:
            return axn_idx

    @staticmethod
    def _reverse_actions(target_prefix, num_unlink_pkgs, pkg_idx, pkg_data, actions,
                         reverse_from_idx=-1):
        # reverse_from_idx = -1 means reverse all actions
        dist = Dist(pkg_data)
        is_unlink = pkg_idx <= num_unlink_pkgs - 1
        if is_unlink:
            log.info("===> REVERSING PACKAGE UNLINK: %s <===\n"
                     "  prefix=%s\n",
                     dist, target_prefix)

        else:
            log.info("===> REVERSING PACKAGE LINK: %s <===\n"
                     "  prefix=%s\n,",
                     dist, target_prefix)

        for action in reversed(actions[:reverse_from_idx]):
            action.reverse()

    @staticmethod
    def get_python_version(target_prefix, linked_packages_data_to_unlink, packages_info_to_link):
        # this method determines the python version that will be present at the
        # end of the transaction
        linking_new_python = next((package_info for package_info in packages_info_to_link
                                   if package_info.index_json_record.name == 'python'),
                                  None)
        if linking_new_python:
            # is python being linked? we're done
            full_version = linking_new_python.index_json_record.version
            assert full_version
            return get_major_minor_version(full_version)

        # is python already linked and not being unlinked? that's ok too
        linked_python_version = get_python_version_for_prefix(target_prefix)
        if linked_python_version:
            find_python = (lnkd_pkg_data for lnkd_pkg_data in linked_packages_data_to_unlink
                           if lnkd_pkg_data.name == 'python')
            unlinking_this_python = next(find_python, None)
            if unlinking_this_python is None:
                # python is not being unlinked
                return linked_python_version

        # there won't be any python in the finished environment
        return None

    @staticmethod
    def make_link_actions(transaction_context, package_info, target_prefix, requested_link_type):
        required_quad = transaction_context, package_info, target_prefix, requested_link_type

        file_link_actions = LinkPathAction.create_file_link_actions(*required_quad)
        create_directory_actions = LinkPathAction.create_directory_actions(
            *required_quad, file_link_actions=file_link_actions
        )
        create_menu_actions = MakeMenuAction.create_actions(*required_quad)

        python_entry_point_actions = CreatePythonEntryPointAction.create_actions(*required_quad)
        compile_pyc_actions = CompilePycAction.create_actions(*required_quad,
                                                              file_link_actions=file_link_actions)

        application_entry_point_actions = CreateApplicationEntryPointAction.create_actions(
            *required_quad,
            file_link_actions=file_link_actions,
            python_entry_point_actions=python_entry_point_actions,
        )
        private_envs_meta_actions = CreatePrivateEnvMetaAction(*required_quad)

        all_target_short_paths = tuple(axn.target_short_path for axn in concatv(
            file_link_actions,
            python_entry_point_actions,
            compile_pyc_actions,
            application_entry_point_actions,
        ))
        meta_create_actions = CreateLinkedPackageRecordAction.create_actions(
            *required_quad, all_target_short_paths=all_target_short_paths
        )

        # the ordering here is significant
        return tuple(concatv(
            create_directory_actions,
            file_link_actions,
            python_entry_point_actions,
            compile_pyc_actions,
            create_menu_actions,
            application_entry_point_actions,
            private_envs_meta_actions,
            meta_create_actions,
        ))


def run_script(prefix, dist, action='post-link', env_prefix=None):
    """
    call the post-link (or pre-unlink) script, and return True on success,
    False on failure
    """
    path = join(prefix, 'Scripts' if on_win else 'bin', '.%s-%s.%s' % (
        dist.dist_name,
        action,
        'bat' if on_win else 'sh'))
    if not isfile(path):
        return True
    if on_win:
        try:
            args = [os.environ['COMSPEC'], '/c', path]
        except KeyError:
            return False
    else:
        shell_path = '/bin/sh' if 'bsd' in sys.platform else '/bin/bash'
        args = [shell_path, path]
    env = os.environ.copy()
    name, version, _, _ = dist.quad
    build_number = dist.build_number
    env[str('ROOT_PREFIX')] = sys.prefix
    env[str('PREFIX')] = str(env_prefix or prefix)
    env[str('PKG_NAME')] = name
    env[str('PKG_VERSION')] = version
    env[str('PKG_BUILDNUM')] = build_number
    if action == 'pre-link':
        env[str('SOURCE_DIR')] = str(prefix)
        warnings.warn(dals("""
        Package %s uses a pre-link script. Pre-link scripts are potentially dangerous.
        This is because pre-link scripts have the ability to change the package contents in the
        package cache, and therefore modify the underlying files for already-created conda
        environments.  Future versions of conda may deprecate and ignore pre-link scripts.
        """ % dist))
    try:
        log.debug("for %s at %s, executing script: $ %s", dist, env_prefix, ' '.join(args))
        check_call(args, env=env)
    except CalledProcessError:
        return False
    else:
        return True
    finally:
        messages(prefix)


def messages(prefix):
    path = join(prefix, '.messages.txt')
    if isfile(path):
        with open(path) as fi:
            fh = sys.stderr if context.json else sys.stdout
            fh.write(fi.read())
        rm_rf(path)
