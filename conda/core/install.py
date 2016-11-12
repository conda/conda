# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import sys
import warnings
from collections import namedtuple
from logging import getLogger
from os import listdir
from os.path import dirname, isdir, isfile, join
from subprocess import CalledProcessError, check_call

from .package_cache import is_extracted, read_url
from ..base.constants import LinkType
from ..base.context import context
from ..common.path import explode_directories, get_leaf_directories, get_bin_directory_short_path, \
    win_path_ok
from ..core.linked_data import (delete_linked_data, get_python_version_for_prefix, load_meta,
                                set_linked_data)
from ..exceptions import CondaOSError, LinkError, PaddingError
from ..gateways.disk.create import (compile_missing_pyc, create_entry_point, link as create_link,
                                    make_menu, mkdir_p, write_conda_meta_record)
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.read import collect_all_info_for_package, yield_lines
from ..gateways.disk.update import _PaddingError, update_prefix
from ..models.record import Link
from ..utils import on_win

try:
    from cytoolz.itertoolz import concatv, groupby
except ImportError:
    from .._vendor.toolz.itertoolz import concatv, groupby  # NOQA

log = getLogger(__name__)

MENU_RE = re.compile(r'^menu/.*\.json$', re.IGNORECASE)
LinkOperation = namedtuple('LinkOperation',
                           ('source_short_path', 'dest_short_path', 'link_type',
                            'prefix_placeholder', 'file_mode', 'is_menu_file'))


def get_package_installer(prefix, index, dist):
    # a factory-type function for getting the correct PackageInstaller class
    record = index.get(dist, None)  # None can happen when handing .tar.bz2 file paths at the CLI
    if record and record.noarch and record.noarch.lower() == 'python':
        return NoarchPythonPackageInstaller(prefix, index, dist)
    else:
        return PackageInstaller(prefix, index, dist)


class PackageInstaller(object):

    def __init__(self, prefix, index, dist):
        self.prefix = prefix
        self.index = index
        self.dist = dist
        self.package_info = None  # set in the link method

    def link(self, requested_link_type=LinkType.hard_link):
        log.debug("linking package %s with link type %s", self.dist, requested_link_type)
        self.extracted_package_dir = is_extracted(self.dist)
        assert self.extracted_package_dir is not None
        log.debug("linking package:\n"
                  "  prefix=%s\n"
                  "  source=%s\n"
                  "  link_type=%s\n",
                  self.prefix, self.extracted_package_dir, requested_link_type)

        # filesystem read actions
        #   do all filesystem reads necessary for the rest of the linking for this package
        self.package_info = collect_all_info_for_package(self.extracted_package_dir)
        url = read_url(self.dist)  # TODO: consider making this part of package_info

        # simple processing
        operations = self._make_link_operations(requested_link_type)
        leaf_directories = get_leaf_directories(op.dest_short_path for op in operations)

        # # run pre-link script
        # if not run_script(extracted_package_dir, self.dist, 'pre-link', self.prefix):
        #     raise LinkError('Error: pre-link failed: %s' % self.dist)

        dest_short_paths = self._execute_link_operations(leaf_directories, operations)

        # run post-link script
        if not run_script(self.prefix, self.dist, 'post-link'):
            raise LinkError("Error: post-link failed for: %s" % self.dist)

        # create package's prefix/conda-meta file
        meta_record = self._create_meta(dest_short_paths, requested_link_type, url)
        write_conda_meta_record(self.prefix, meta_record)
        set_linked_data(self.prefix, self.dist.dist_name, meta_record)

    def _make_link_operations(self, requested_link_type):
        # no side effects in this method!
        package_info = self.package_info

        def make_link_operation(source_short_path):
            if source_short_path in package_info.has_prefix_files:
                link_type = LinkType.copy
                prefix_placehoder, file_mode = package_info.has_prefix_files[source_short_path]
            elif source_short_path in concatv(package_info.no_link, package_info.soft_links):
                link_type = LinkType.copy
                prefix_placehoder, file_mode = '', None
            else:
                link_type = requested_link_type
                prefix_placehoder, file_mode = '', None
            is_menu_file = bool(MENU_RE.match(source_short_path))
            dest_short_path = source_short_path
            return LinkOperation(source_short_path, dest_short_path, link_type, prefix_placehoder,
                                 file_mode, is_menu_file)
        return tuple(make_link_operation(p) for p in package_info.files)

    def _execute_link_operations(self, leaf_directories, link_operations):
        # major side-effects in this method

        dest_short_paths = []

        # Step 1. Make all directories
        for leaf_directory in leaf_directories:
            mkdir_p(join(self.prefix, win_path_ok(leaf_directory)))

        # Step 2. Do the actual file linking
        for op in link_operations:
            try:
                create_link(join(self.extracted_package_dir, win_path_ok(op.source_short_path)),
                            join(self.prefix, win_path_ok(op.dest_short_path)),
                            op.link_type)
                dest_short_paths.append(op.dest_short_path)
            except OSError as e:
                raise CondaOSError('failed to link (src=%r, dst=%r, type=%r, error=%r)' %
                                   (op.source_path, op.dest_path, op.link_type, e))

        # Step 3. Replace prefix placeholder within all necessary files
        # Step 4. Make shortcuts on Windows
        for op in link_operations:
            if op.prefix_placeholder:
                try:
                    update_prefix(join(self.prefix, win_path_ok(op.dest_short_path)), self.prefix,
                                  op.prefix_placeholder, op.file_mode)
                except _PaddingError:
                    raise PaddingError(op.dest_path, op.prefix_placeholder,
                                       len(op.prefix_placeholder))
            if on_win and op.is_menu_file and context.shortcuts:
                make_menu(self.prefix, win_path_ok(op.dest_short_path), remove=False)

        if on_win:
            # make sure that the child environment behaves like the parent,
            #    wrt user/system install on win
            # This is critical for doing shortcuts correctly
            # TODO: I don't understand; talk to @msarahan
            # TODO: sys.prefix is almost certainly *wrong* here
            nonadmin = join(sys.prefix, ".nonadmin")
            if isfile(nonadmin):
                open(join(self.prefix, ".nonadmin"), 'w').close()

        return dest_short_paths

    def _create_meta(self, dest_short_paths, requested_link_type, url):
        """
        Create the conda metadata, in a given prefix, for a given package.
        """
        package_info = self.package_info
        meta_dict = self.index.get(self.dist, {})
        meta_dict['url'] = url

        # alt_files_path is a hack for python_noarch
        alt_files_path = join(self.prefix, 'conda-meta', self.dist.to_filename('.files'))
        meta_dict['files'] = (list(yield_lines(alt_files_path)) if isfile(alt_files_path)
                              else dest_short_paths)
        meta_dict['link'] = Link(source=self.extracted_package_dir, type=requested_link_type)
        if 'icon' in meta_dict:
            meta_dict['icondata'] = package_info.icondata

        meta = package_info.index_json_record
        meta.update(meta_dict)

        return meta


class NoarchPythonPackageInstaller(PackageInstaller):

    def _make_link_operations(self, requested_link_type):
        package_info = self.package_info
        site_packages_dir = NoarchPythonPackageInstaller.get_site_packages_dir(self.prefix)
        bin_dir = get_bin_directory_short_path()

        def make_link_operation(source_short_path):
            # no side effects in this method!

            # first part, same as parent class
            if source_short_path in package_info.has_prefix_files:
                link_type = LinkType.copy
                prefix_placehoder, file_mode = package_info.has_prefix_files[source_short_path]
            elif source_short_path in concatv(package_info.no_link, package_info.soft_links):
                link_type = LinkType.copy
                prefix_placehoder, file_mode = '', None
            else:
                link_type = requested_link_type
                prefix_placehoder, file_mode = '', None
            is_menu_file = bool(MENU_RE.match(source_short_path))

            # second part, noarch python-specific
            if source_short_path.startswith('site-packages/'):
                dest_short_path = site_packages_dir + source_short_path.replace(
                    'site-packages', '', 1)
            elif source_short_path.startswith('python-scripts/'):
                dest_short_path = bin_dir + source_short_path.replace('python-scripts', '', 1)
            else:
                dest_short_path = source_short_path
            return LinkOperation(source_short_path, dest_short_path, link_type, prefix_placehoder,
                                 file_mode, is_menu_file)

        return tuple(make_link_operation(p) for p in package_info.files)

    def _execute_link_operations(self, leaf_directories, link_operations):
        dest_short_paths = super(NoarchPythonPackageInstaller, self)._execute_link_operations(
            leaf_directories, link_operations)

        # create pyc files
        python_veresion = get_python_version_for_prefix(self.prefix)
        extra_pyc_paths = compile_missing_pyc(self.prefix, python_veresion,
                                              tuple(op.dest_short_path for op in link_operations))

        # create entry points
        entry_points = self.package_info.noarch.get('entry_points', ())
        entry_point_paths = []
        for entry_point in entry_points:
            entry_point_paths.extend(create_entry_point(entry_point, self.prefix))

        return sorted(concatv(dest_short_paths, extra_pyc_paths, entry_point_paths))

    @staticmethod
    def get_site_packages_dir(prefix):
        if on_win:
            return 'Lib/site-packages'
        else:
            return 'lib/python%s/site-packages' % get_python_version_for_prefix(prefix)


class PackageUninstaller(object):

    def __init__(self, prefix, dist):
        self.prefix = prefix
        self.dist = dist

    def unlink(self):
        """
        Remove a package from the specified environment, it is an error if the
        package does not exist in the prefix.
        """
        log.debug("unlinking package %s", self.dist)
        run_script(self.prefix, self.dist, 'pre-unlink')

        meta = load_meta(self.prefix, self.dist)

        dirs_with_removals = set()

        for f in meta['files']:
            if on_win and bool(MENU_RE.match(f)):
                # Always try to run this - it should not throw errors where menus do not exist
                # note that it will probably remove the file though; rm_rf shouldn't care
                make_menu(self.prefix, win_path_ok(f), remove=True)

            dirs_with_removals.add(dirname(f))
            rm_rf(join(self.prefix, win_path_ok(f)))

        # remove the meta-file last
        delete_linked_data(self.prefix, self.dist, delete=True)

        dirs_with_removals.add('conda-meta')  # in case there is nothing left
        directory_removal_candidates = (join(self.prefix, win_path_ok(d)) for d in
                                        sorted(explode_directories(dirs_with_removals),
                                               reverse=True))

        # remove empty directories
        for d in directory_removal_candidates:
            if isdir(d) and not listdir(d):
                rm_rf(d)

        alt_files_path = join(self.prefix, 'conda-meta', self.dist.to_filename('.files'))
        if isfile(alt_files_path):
            rm_rf(alt_files_path)


def run_script(prefix, dist, action='post-link', env_prefix=None):
    """
    call the post-link (or pre-unlink) script, and return True on success,
    False on failure
    """
    if action == 'pre-link':
        warnings.warn("The package %s uses a pre-link script.\n"
                      "Pre-link scripts may be deprecated in the near future.")
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
    build_number = dist.build_number()
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
