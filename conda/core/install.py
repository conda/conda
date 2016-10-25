# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import sys
import warnings
from collections import namedtuple
from logging import getLogger
from os.path import isfile, join
from subprocess import CalledProcessError, check_call

from .package_cache import is_extracted, read_url
from ..base.constants import LinkType
from ..base.context import context
from ..common.path import get_leaf_directories
from ..core.linked_data import set_linked_data
from ..exceptions import CondaOSError, LinkError, PaddingError
from ..gateways.disk.create import link as create_link, make_menu, mkdir_p, write_conda_meta_record
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


class PackageInstaller(object):

    def __init__(self, prefix, index, dist):
        self.prefix = prefix
        self.index = index
        self.dist = dist

    def link(self, requested_link_type=LinkType.hard_link):
        log.debug("linking package %s with link type %s", self.dist, requested_link_type)
        extracted_package_directory = is_extracted(self.dist)
        assert extracted_package_directory is not None
        log.debug("linking package:\n"
                  "  prefix=%s\n"
                  "  source=%s\n"
                  "  link_type=%s\n",
                  self.prefix, extracted_package_directory, requested_link_type)

        # filesystem read actions
        #   do all filesystem reads necessaary for the rest of the linking for this package
        package_info = collect_all_info_for_package(extracted_package_directory)
        url = read_url(self.dist)

        # simple processing
        operations = self.make_link_operations(extracted_package_directory, self.prefix,
                                               requested_link_type, package_info)
        leaf_directories = get_leaf_directories(op.destination_path for op in operations)

        # run pre-link script
        if not run_script(extracted_package_directory, self.dist, 'pre-link', self.prefix):
            raise LinkError('Error: pre-link failed: %s' % self.dist)

        self.execute_link_operations(self.prefix, leaf_directories, operations)

        # run post-link script
        if not run_script(self.prefix, self.dist, 'post-link'):
            raise LinkError("Error: post-link failed for: %s" % self.dist)

        # create package's prefix/conda-meta file
        meta_record = self.create_meta(extracted_package_directory, package_info,
                                       requested_link_type, self.prefix, self.dist,
                                       self.index, url)
        write_conda_meta_record(self.prefix, meta_record)
        set_linked_data(self.prefix, self.dist.dist_name, meta_record)

    @staticmethod
    def make_link_operations(extracted_package_directory, prefix, requested_link_type,
                             package_info):
        MENU_RE = re.compile(r'^menu/.*\.json$', re.IGNORECASE)
        LinkOperation = namedtuple('LinkOperation',
                                   ('short_path', 'source_path', 'destination_path', 'link_type',
                                    'prefix_placehoder', 'file_mode', 'is_menu_file'))

        def make_link_operation(short_path):
            if short_path in package_info.has_prefix_files:
                link_type = LinkType.copy
                prefix_placehoder, file_mode = package_info.has_prefix_files[short_path]
            elif short_path in package_info.no_link or short_path in package_info.soft_links:
                link_type = LinkType.copy
                prefix_placehoder, file_mode = '', None
            else:
                link_type = requested_link_type
                prefix_placehoder, file_mode = '', None
            is_menu_file = bool(MENU_RE.match(short_path))
            source_path = join(extracted_package_directory, short_path)
            destination_path = join(prefix, short_path)
            return LinkOperation(source_path, destination_path, short_path, link_type,
                                 prefix_placehoder, file_mode, is_menu_file)

        return (make_link_operation(p) for p in package_info.files)

    @staticmethod
    def execute_link_operations(prefix, leaf_directories, link_operations):
        # Step 1. Make all directories
        for leaf_directory in leaf_directories:
            mkdir_p(leaf_directory)

        # Step 2. Do the actual file linking
        for op in link_operations:
            try:
                create_link(op.source_path, op.destination_path, op.link_type)
            except OSError as e:
                raise CondaOSError('failed to link (src=%r, dst=%r, type=%r, error=%r)' %
                                   (op.source_path, op.destination_path, op.link_type, e))

        # Step 3. Replace prefix placeholder within all necessary files
        # Step 4. Make shortcuts on Windows
        for op in link_operations:
            if op.prefix_placeholder:
                try:
                    update_prefix(op.destination_path, prefix, op.prefix_placeholder, op.file_mode)
                except _PaddingError:
                    raise PaddingError(op.destination_path, op.prefix_placeholder,
                                       len(op.prefix_placeholder))
            if on_win and op.is_menu_file and context.shortcuts:
                make_menu(prefix, op.short_path, remove=False)

        if on_win:
            # make sure that the child environment behaves like the parent,
            #    wrt user/system install on win
            # This is critical for doing shortcuts correctly
            # TODO: I don't understand; talk to @msarahan
            # TODO: sys.prefix is almost certainly *wrong* here
            nonadmin = join(sys.prefix, ".nonadmin")
            if isfile(nonadmin):
                open(join(prefix, ".nonadmin"), 'w').close()

    @staticmethod
    def create_meta(extracted_package_directory, package_info, prefix, dist, requested_link_type,
                    index, url):
        """
        Create the conda metadata, in a given prefix, for a given package.
        """
        meta_dict = index.get(dist, {})
        meta_dict['url'] = url

        # alt_files_path is a hack for python_noarch
        alt_files_path = join(prefix, 'conda-meta', dist.to_filename('.files'))
        meta_dict['files'] = (list(yield_lines(alt_files_path)) if isfile(alt_files_path)
                              else package_info.files)
        meta_dict['link'] = Link(source=extracted_package_directory, type=requested_link_type)
        if 'icon' in meta_dict:
            meta_dict['icondata'] = package_info.icondata

        meta = package_info.index_json_record
        meta.update(meta_dict)

        return meta


class NoarchPythonPackageInstaller(PackageInstaller):
    pass


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
