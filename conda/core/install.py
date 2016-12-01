# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import sys
import warnings
from conda import CONDA_PACKAGE_ROOT
from conda.compat import string_types
from conda.core.path_actions import CompilePycAction, CreateCondaMetaAction, \
    CreatePythonEntryPointAction, LinkPathAction, MakeMenuAction, PrefixReplaceLinkAction
from logging import getLogger
from os.path import dirname, join
from subprocess import CalledProcessError, check_call

from .._vendor.auxlib.ish import dals
from ..base.constants import LinkType
from ..base.context import context
from ..common.path import explode_directories, get_all_directories, get_bin_directory_short_path, \
    get_leaf_directories, parse_entry_point_def, win_path_ok
from ..core.linked_data import (delete_linked_data, linked_data, load_meta)
from ..gateways.disk.create import hardlink_supported, make_menu, softlink_supported
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.read import isdir, isfile
from ..models.package_info import PathType
from ..models.record import Link, Record
from ..utils import on_win

try:
    from cytoolz.itertoolz import concat, concatv, groupby
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv, groupby  # NOQA

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
    link_type, prefix_placehoder, file_mode = get_prefix_replace(source_path_info, requested_link_type)
    return LinkPathAction(extracted_package_dir, short_path,
                          target_prefix, short_path, link_type,
                          prefix_placehoder, file_mode)



def get_python_noarch_target_path(source_short_path):
    if source_short_path.startswith('site-packages/'):
        sp_dir = '%(target_site_packages_short_path)s'
        # string interpolation done when necessary in the action
        return source_short_path.replace('site-packages', sp_dir, 1)
    elif source_short_path.startswith('python-scripts/'):
        bin_dir = '%(target_bin_dir)s'
        return source_short_path.replace('python-scripts', bin_dir, 1)
    else:
        return source_short_path



def make_link_actions(transaction_context, package_info, target_prefix, requested_link_type):
    # no side effects in this function!

    def make_directory_link_action(directory_short_path):
        # no side effects in this function!
        return LinkPathAction(None, None, target_prefix, directory_short_path, LinkType.directory,
                              None, None)

    def make_file_link_action(source_path_info):

        noarch = package_info.noarch
        if noarch and noarch.type == 'python':
            target_short_path = get_python_noarch_target_path(source_path_info.path)
        elif not noarch or noarch is True or (isinstance(noarch, string_types)
                                              and noarch == 'native'):
            target_short_path = source_path_info.path
        else:
            # TODO: need an error message
            raise CondaUpgradeError()

        link_type, placeholder, fmode = get_prefix_replace(source_path_info, requested_link_type)

        if placeholder:
            assert link_type == LinkType.copy
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
        meta_record =  Record.from_objects(package_info.repodata_record,
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

    if package_info.noarch.type == 'python':
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


    all_target_short_paths = concat(file_link_actions, python_entry_point_actions, pyc_compile_actions)
    meta_create_actions = (make_conda_meta_create_action(all_target_short_paths),)

    return tuple(concatv(directory_create_actions, file_link_actions, python_entry_point_actions,
                         pyc_compile_actions,  menu_create_actions, meta_create_actions))


def make_unlink_actions(transaction_context, pkg_info, target_prefix):
    pass


class UnlinkLinkTransaction(object):

    def __init__(self, target_prefix, unlink_dists, link_dists):
        # type: (str, Sequence[Dist], Sequence[PackageInfo]])
        # order of unlink_dists and link_dists will be preserved throughout
        #   should be given in dependency-sorted order

        # gather information from disk and caches
        self.prefix_linked_data = linked_data(target_prefix)
        self.prefix_inventory = inventory_prefix(target_prefix)
        self.unlink_dists = unlink_dists
        self.link_packages_info = link_dists

        link_types = [determine_link_type(extracted_package_dir, target_prefix) for dist in link_dists]

        # make all the path_actions
        # No side effects!  All disk access should be done in the section above.
        # first unlink action should be conda-meta json file, because it will roll back
        # last link action should be conda-meta json file

        transaction_context = dict()
        self.unlink_actions = tuple((dist, make_unlink_actions(dist)) for dist in self.unlink_dists)

        self.link_actions = (make_link_actions(transaction_context, pkg_info, target_prefix, lt) for pkg_info, lt in zip(self.link_packages_info, link_types))

        # we won't definitively know location of site-packages until here
        transaction_context['target_bin_dir']
        transaction_context['target_python_version']
        transaction_context['target_site_packages_short_path']

        # verify link sources
        # for each LinkPathAction where extracted_package_dir and source_short_path are not None,
        # verify that the file is visible
        # in the future, consider checking hashsums

        # verify link destinations
        # make sure path doesn't exist or will be unlinked first
        [axn.verify() for axn in self.unlink_actions]
        [axn.verify() for axn in self.link_actions]


        # execute the transaction
        try:
            for q, dist, unlink_actions in enumerate(self.unlink_actions):
                run_script(target_prefix, dist, 'pre-unlink')
                
                for p, unlink_action in enumerate(unlink_actions):
                    unlink_action.execute()

                run_script(target_prefix, dist, 'post-unlink')
                
                # now here put in try/except/else for link
                # don't forget the PITA noarch_python
                try:
                    for n, dist, link_actions in enumerate(self.link_actions):
                        run_script(target_prefix, dist, 'pre-link')

                        for m, link_action in enumerate(link_actions):
                            link_action.execute()

                        run_script(target_prefix, dist, 'post-link')

                except Exception as e:
                    # print big explanatory error message
                    rollback_from = n, m
                    raise
                else:
                    for n, dist, link_actions in enumerate(self.link_actions):
                        for m, link_action in enumerate(link_actions):
                            link_action.cleanup()

        except Exception as e:
            # print big explanatory error message
            rollback_from = q, p
        else:
            for q, dist, unlink_actions in enumerate(self.unlink_actions):
                for p, unlink_action in enumerate(unlink_actions):
                    unlink_action.cleanup()






        # # create per-path unlink and link directives, grouped by dist, in dependency-sorted order
        # # self.unlink_directives = tuple((dist, self._make_unlink_operations(dist)) for dist in self.unlink_dists)
        # # # type: Tuple[Tuple[package_name, Tuple[UnlinkOperation]]]
        # self.package_unlinkers = tuple(PackageUnlinker(dist) for dist in self.unlink_dists)
        #
        # # self.link_directives = self._make_link_operations()
        # # # type: Tuple[Tuple[package_name, Tuple[LinkOperation]]]
        # self.package_linkers = tuple(PackageLinker(package_info) for package_info in self.link_packages_info)


        # # unlink
        # #   - assert can remove file
        # #     implies write access within parent directory on unix
        # #   - as assertions are executed, remove file from prefix_inventory
        # for unlinker in self.package_unlinkers:
        #     for directive in unlinker.directives:
        #         assert can_unlink(directive.path), unlinker.package_name
        #         # remove path from prefix_inventory
        #
        # # package cache
        # #   - assert all files exist and visible
        # #   - (maybe?) assert per-file sha sums
        # for package_info in self.link_packages_info:
        #     assert join(package_info.package_full_path, )
        #
        # # link
        # #   - build assertions based on algorithm
        # #   - as assertions are executed, add paths to prefix_inventory
        #
        # #   - create assertions, for both package cache and target_prefix
        # #   - run assertions against file system

        # execute unlink and link directives


    def _make_unlink_operations(self, dist):
        linked_package_data = self.prefix_linked_data[dist]
        package_files = linked_package_data.files
        all_directories = sorted(get_all_directories(package_files), key=len, reverse=True)

        def make_file_unlink_operation(path):
            prefix_short_path = path
            is_menu_file = bool(MENU_RE.match(path))
            # using hardlink here, because treatment would be no different than softlink
            return UnlinkOperation(prefix_short_path, is_menu_file, PathType.hardlink)

        def make_dir_unlink_operation(path):
            return UnlinkOperation(path, False, PathType.directory)

        return tuple(concatv(
            (make_file_unlink_operation(p) for p in package_files),
            (make_dir_unlink_operation(d) for d in all_directories),
        ))





class PackageUninstaller(object):

    def __init__(self, prefix, dist):
        self.prefix = prefix
        self.dist = dist
        self.linked_data = None

    def unlink(self):
        """
        Remove a package from the specified environment, it is an error if the
        package does not exist in the prefix.
        """
        log.debug("unlinking package %s", self.dist)
        run_script(self.prefix, self.dist, 'pre-unlink')

        # file system reads
        self.linked_data = linked_data(self.prefix)
        meta = load_meta(self.prefix, self.dist)

        # computations
        self._make_unlink_operations()
        # files = meta['files']


        dirs_with_removals = set()

        for f in meta['files']:
            if on_win and bool(MENU_RE.match(f)):
                # Always try to run this - it should not throw errors where menus do not exist
                # note that it will probably remove the file though; rm_rf shouldn't care
                make_menu(self.prefix, win_path_ok(f), remove=True)

            dirs_with_removals.add(dirname(f))
            rm_rf(join(self.prefix, win_path_ok(f)))

        # remove the meta-file last
        #   TODO: why last?  Won't that leave things more broken than removing it first?
        #   maybe should rename the file with an extra extension, then remove it once the
        #   operation is complete
        delete_linked_data(self.prefix, self.dist, delete=True)

        dirs_with_removals.add('conda-meta')  # in case there is nothing left
        directory_removal_candidates = (join(self.prefix, win_path_ok(d)) for d in
                                        sorted(explode_directories(dirs_with_removals),
                                               reverse=True))

        # remove empty directories; don't crash if we can't
        for d in directory_removal_candidates:
            if isdir(d) and not listdir(d):
                try:
                    rm_rf(d)
                except (IOError, OSError) as e:
                    log.debug("Failed to remove '%s'. %r", d, e)

        alt_files_path = join(self.prefix, 'conda-meta', self.dist.to_filename('.files'))
        if isfile(alt_files_path):
            rm_rf(alt_files_path)


def run_script(prefix, dist, action='post-link', env_prefix=None):
    """
    call the post-link (or pre-unlink) script, and return True on success,
    False on failure
    """
    if action == 'pre-link':
        warnings.warn(dals("""
        Package %s uses a pre-link script. Pre-link scripts are potentially dangerous.
        This is because pre-link scripts have the ability to change the package contents in the
        package cache, and therefore modify the underlying files for already-created conda
        environments.  Future versions of conda may deprecate and ignore pre-link scripts.
        """ % dist))

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





