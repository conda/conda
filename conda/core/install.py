# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import sys
import warnings
from conda.exceptions import CondaUpgradeError
from conda.models.dist import Dist
from logging import getLogger
from os.path import join
from subprocess import CalledProcessError, check_call

from .. import CONDA_PACKAGE_ROOT
from .._vendor.auxlib.ish import dals
from ..base.constants import LinkType
from ..base.context import context
from ..common.path import (get_all_directories, get_bin_directory_short_path,
                           get_leaf_directories, parse_entry_point_def,
                           get_major_minor_version, get_python_site_packages_short_path,
                           explode_directories)
from ..compat import string_types
from ..core.linked_data import linked_data as get_linked_data, get_python_version_for_prefix
from ..core.path_actions import (CompilePycAction, CreateCondaMetaAction,
                                 CreatePythonEntryPointAction, LinkPathAction, MakeMenuAction,
                                 PrefixReplaceLinkAction, UnlinkPathAction, RemoveMenuAction,
                                 RemoveCondaMetaAction, RemovePathAction, CreatePathAction)
from ..gateways.disk.create import hardlink_supported, softlink_supported
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.read import isfile
from ..models.package_info import PathType
from ..models.record import Link, Record
from ..utils import on_win

try:
    from cytoolz.itertoolz import concat, concatv
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv  # NOQA

log = getLogger(__name__)

MENU_RE = re.compile(r'^menu/.*\.json$', re.IGNORECASE)


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


def make_lateral_link_action(source_path_info, extracted_package_dir, target_prefix,
                             requested_link_type):
    # no side effects in this function!
    # a lateral link has the same 'short path' in both the package directory and the target prefix
    short_path = source_path_info.path
    link_type, prefix_placehoder, file_mode = get_prefix_replace(source_path_info,
                                                                 requested_link_type)
    return LinkPathAction(extracted_package_dir, short_path,
                          target_prefix, short_path, link_type,
                          prefix_placehoder, file_mode)


def get_python_noarch_target_path(source_short_path):
    if source_short_path.startswith('site-packages/'):
        sp_dir = '{target_site_packages_short_path}'
        # string interpolation done when necessary in the action
        return source_short_path.replace('site-packages', sp_dir, 1)
    elif source_short_path.startswith('python-scripts/'):
        bin_dir = get_bin_directory_short_path()
        return source_short_path.replace('python-scripts', bin_dir, 1)
    else:
        return source_short_path


def make_link_actions(transaction_context, package_info, target_prefix, requested_link_type):
    # no side effects in this function!
    # TODO: clean up this monstrosity of a function

    def make_directory_link_action(directory_short_path):
        # no side effects in this function!
        return LinkPathAction(transaction_context, package_info, None, None,
                              target_prefix, directory_short_path, LinkType.directory)

    def make_file_link_action(source_path_info):

        noarch = package_info.noarch
        if noarch and noarch.type == 'python':
            target_short_path = get_python_noarch_target_path(source_path_info.path)
        elif not noarch or noarch is True or (isinstance(noarch, string_types)
                                              and noarch == 'native'):
            target_short_path = source_path_info.path
        else:
            raise CondaUpgradeError(dals("""
            The current version of conda is too old to install this package.
            Please update conda."""))

        link_type, placeholder, fmode = get_prefix_replace(source_path_info, requested_link_type)

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

    def make_entry_point_action(entry_point_def):
        command, module, func = parse_entry_point_def(entry_point_def)
        target_short_path = "%s/%s" % (get_bin_directory_short_path(), command)
        CreatePythonEntryPointAction(transaction_context, package_info,
                                     target_prefix, target_short_path, module, func)

    def make_entry_point_windows_executable_action(entry_point_def):
        source_directory = CONDA_PACKAGE_ROOT
        source_short_path = 'resources/cli-%d.exe' % context.bits
        command, _, _ = parse_entry_point_def(entry_point_def)
        target_short_path = "%s/%s.exe" % (get_bin_directory_short_path(), command)
        LinkPathAction(transaction_context, package_info, source_directory, source_short_path,
                       target_prefix, target_short_path, requested_link_type)

    def make_conda_meta_create_action(all_target_short_paths):
        link = Link(source=package_info.extracted_package_dir, type=requested_link_type)
        meta_record = Record.from_objects(package_info.repodata_record,
                                          package_info.index_json_record,
                                          files=all_target_short_paths, link=link,
                                          url=package_info.url)
        return CreateCondaMetaAction(transaction_context, package_info, target_prefix, meta_record)

    file_link_actions = tuple(make_file_link_action(spi) for spi in package_info.paths)

    leaf_directories = get_leaf_directories(axn.target_short_path for axn in file_link_actions)
    directory_create_actions = tuple(make_directory_link_action(d) for d in leaf_directories)

    if on_win:
        menu_create_actions = tuple(MakeMenuAction(transaction_context, package_info,
                                                   target_prefix, spi.path)
                                    for spi in package_info.paths
                                    if bool(MENU_RE.match(spi.path)))
    else:
        menu_create_actions = ()

    if package_info.noarch and package_info.noarch.type == 'python':
        python_entry_point_actions = tuple(concatv(
            (make_entry_point_action(ep_def) for ep_def in package_info.noarch.entry_points),
            (make_entry_point_windows_executable_action(ep_def)
             for ep_def in package_info.noarch.entry_points) if on_win else (),
        ))

        py_files = (axn for axn in file_link_actions if axn.source_short_path.endswith('.py'))
        pyc_compile_actions = tuple(CompilePycAction(transaction_context, package_info,
                                                     target_prefix, pf) for pf in py_files)
    else:
        python_entry_point_actions = ()
        pyc_compile_actions = ()

    all_target_short_paths = (axn.target_short_path for axn in
                              concatv(file_link_actions,
                                      python_entry_point_actions,
                                      pyc_compile_actions))
    meta_create_actions = (make_conda_meta_create_action(all_target_short_paths),)

    return tuple(concatv(directory_create_actions, file_link_actions, python_entry_point_actions,
                         pyc_compile_actions,  menu_create_actions, meta_create_actions))


def make_unlink_actions(transaction_context, target_prefix, linked_package_data):
    # no side effects in this function!
    unlink_path_actions = tuple(UnlinkPathAction(transaction_context, linked_package_data,
                                                 target_prefix, trgt)
                                for trgt in linked_package_data.files)
    if on_win:
        remove_menu_actions = tuple(RemoveMenuAction(transaction_context, linked_package_data,
                                                     target_prefix, trgt)
                                    for trgt in linked_package_data.files
                                    if bool(MENU_RE.match(trgt)))
    else:
        remove_menu_actions = ()

    meta_short_path = '%s/%s' % ('conda-meta', Dist(linked_package_data).to_filename('.json'))
    remove_conda_meta_actions = (RemoveCondaMetaAction(transaction_context, linked_package_data,
                                                       target_prefix, meta_short_path),)

    _all_d = get_all_directories(axn.target_short_path for axn in unlink_path_actions)
    all_directories = sorted(explode_directories(_all_d, already_split=True))
    directory_remove_actions = tuple(UnlinkPathAction(transaction_context, linked_package_data,
                                                      target_prefix, d, LinkType.directory)
                                     for d in all_directories)
    return tuple(concatv(remove_conda_meta_actions, remove_menu_actions, unlink_path_actions,
                         directory_remove_actions))


class UnlinkLinkTransaction(object):

    def __init__(self, target_prefix, linked_packages_data_to_unlink, packages_info_to_link):
        # type: (str, Sequence[Dist], Sequence[PackageInfo]])
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
        unlink_actions = tuple((lnkd_pkg_data, make_unlink_actions(transaction_context,
                                                                   self.target_prefix,
                                                                   lnkd_pkg_data))
                               for lnkd_pkg_data in self.linked_packages_data_to_unlink)
        link_actions = tuple((pkg_info, make_link_actions(transaction_context, pkg_info,
                                                          self.target_prefix, lt))
                             for pkg_info, lt in zip(self.packages_info_to_link, link_types))
        self.all_actions = tuple(per_pkg_actions for per_pkg_actions in
                                 concatv(unlink_actions, link_actions))
        self.num_unlink_pkgs = len(unlink_actions)

        # we won't definitively know some environment information until here
        #   e.g. python version and site-packages location
        python_version = self.get_python_version(self.target_prefix, unlink_actions, link_actions)
        transaction_context['target_python_version'] = python_version
        sp = get_python_site_packages_short_path(python_version)
        transaction_context['target_site_packages_short_path'] = sp

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
            for pkg_indx, (pkg_data, actions) in enumerate(self.all_actions):
                dist = Dist(pkg_data)
                is_unlink = pkg_indx <= self.num_unlink_pkgs
                if is_unlink:
                    log.info("unlinking package: %s\n"
                             "  prefix=%s\n",
                             dist, self.target_prefix)

                else:
                    log.info("linking package: %s\n"
                             "  prefix=%s\n"
                             "  source=%s\n",
                             dist, self.target_prefix, pkg_data.extracted_package_dir)

                run_script(self.target_prefix, Dist(pkg_data),
                           'pre-unlink' if is_unlink else 'pre-link')

                for axn_idx, action in enumerate(actions):
                    action.execute()

                run_script(self.target_prefix, Dist(pkg_data),
                           'post-unlink' if is_unlink else 'post-link')

        except Exception as e:
            log.error("Something bad happened, but it's okay because I'm going to roll back now.")
            log.exception(e)
            failed_pkg_idx, failed_axn_idx = pkg_indx, axn_idx
            self._reverse_actions(self.all_actions[failed_pkg_idx][1], failed_axn_idx)
            for pkg_indx in reversed(range(failed_pkg_idx)):
                self._reverse_actions(self.all_actions[pkg_indx][1])

        else:
            for pkg_indx, (pkg_data, actions) in enumerate(self.all_actions):
                for axn_idx, action in enumerate(actions):
                    action.cleanup()

    @staticmethod
    def _execute_action(action):

        action.execute()


    @staticmethod
    def _reverse_actions(actions, reverse_from_idx=None):
        reverse_from_idx = reverse_from_idx or len(actions)
        for axn_idx in reversed(range(reverse_from_idx)):
            actions[axn_idx].reverse()

    @staticmethod
    def get_python_version(target_prefix, unlink_actions, link_actions):
        # is python being linked? we're done
        linking_this_python = next((per_pkg_actions for per_pkg_actions in link_actions
                                    if per_pkg_actions[0].index_json_record.name == 'python'),
                                   None)
        if linking_this_python:
            full_version = linking_this_python[0].index_json_record.version
            assert full_version
            return get_major_minor_version(full_version)

        # is python already linked and not being unlinked? that's ok too
        linked_python_version = get_python_version_for_prefix(target_prefix)
        if linked_python_version:
            find_python = (per_pkg_actions for per_pkg_actions in unlink_actions
                           if per_pkg_actions[0].name == 'python')
            unlinking_this_python = next(find_python, None)
            if unlinking_this_python is None:
                # python is not being unlinked
                return linked_python_version


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
