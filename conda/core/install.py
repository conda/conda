# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re

from conda.common.disk import link as disk_link, yield_lines
from conda.common.path import get_leaf_directories
from conda.exceptions import CondaOSError
from enum import Enum
from logging import getLogger
from os import makedirs
from os.path import join, isdir, dirname, islink

log = getLogger(__name__)




LINK_HARD = 1
LINK_SOFT = 2
LINK_COPY = 3
link_name_map = {
    LINK_HARD: 'hard-link',
    LINK_SOFT: 'soft-link',
    LINK_COPY: 'copy',
}




def read_soft_links(extracted_package_directory, files):
    return tuple(f for f in files if islink(join(extracted_package_directory, f)))


def collect_all_info_for_package(extracted_package_directory):
    info_dir = join(extracted_package_directory, 'info')

    # collect information from info directory
    from ..install import read_has_prefix, read_no_link
    files = tuple(yield_lines(join(extracted_package_directory, 'info', 'files')))

    # file system calls
    has_prefix_files = read_has_prefix(join(info_dir, 'has_prefix'))
    no_link = read_no_link(info_dir)
    soft_links = read_soft_links(extracted_package_directory, files)

    # simple processing
    MENU_RE = re.compile(r'^menu/.*\.json$', re.IGNORECASE)
    menu_files = tuple(f for f in files if MENU_RE.match(f))

    return files, has_prefix_files, no_link, soft_links, menu_files



def make_op_details(files, has_prefix_files, no_link, soft_links, menu_files, requested_link_type):
    file_operations = []
    for filepath in files:
        if filepath in has_prefix_files:
            link_type = LINK_COPY
            prefix_placehoder, file_mode = has_prefix_files[filepath]
        elif filepath in no_link or filepath in soft_links:
            link_type = LINK_COPY
            prefix_placehoder, file_mode = None, None
        else:
            link_type = requested_link_type
            prefix_placehoder, file_mode = None, None
        is_menu_file = filepath in menu_files
        file_operations.append((filepath, link_type, prefix_placehoder, file_mode, is_menu_file))

    # file_paths, link_types, prefix_placeholders, file_modes, is_menu_file
    return file_operations


def execute_file_operations(extracted_package_directory, prefix, leaf_directories, file_operations):

        # Step 1. Make all directories
        for d in leaf_directories:
            makedirs(join(prefix, d), exist_ok=True)

        # Step 2. Do the actual file linking
        # Step 3. Replace prefix placeholder within all necessary files
        # Step 4. Make shortcuts on Windows
        for file_path, link_type, prefix_placeholder, file_mode, is_menu_file in file_operations:
            source_path = join(extracted_package_directory, file_path)
            destination_path = join(prefix, file_path)
            try:
                disk_link(source_path, destination_path, link_type)
            except OSError as e:
                raise CondaOSError('failed to link (src=%r, dst=%r, type=%r, error=%r)' %
                                   (src, dst, lt, e))
            if prefix_placeholder:
                try:
                    update_prefix(destination_path, prefix, prefix_placeholder, file_mode)
                except _PaddingError:
                    raise PaddingError(dist, prefix_placeholder, len(prefix_placeholder))

            if on_win and is_menu_file and context.shortcuts:
                make_menu(source_path, remove=False)

        if on_win:
            # make sure that the child environment behaves like the parent,
            #    wrt user/system install on win
            # This is critical for doing shortcuts correctly
            # TODO: I don't understand; talk to @msarahan
            nonadmin = join(sys.prefix, ".nonadmin")
            if isfile(nonadmin):
                open(join(prefix, ".nonadmin"), 'w').close()




class PackageInstaller(object):

    def __init__(self, prefix, extracted_package_directory, record):
        self.prefix = prefix
        self.extracted_package_directory = extracted_package_directory
        self.record = record

    def link(self, requested_link_type='LINK_HARD'):
        log.debug("linking package:\n"
                  "  prefix=%s\n"
                  "  source=%s\n"
                  "  link_type=%s\n",
                  self.prefix, self.extracted_package_directory, link_type)

        source_dir = self.extracted_package_directory

        files, has_prefix_files, no_link, soft_links, menu_files = collect_all_info_for_package(self.extracted_package_directory)
        leaf_directories = get_leaf_directories(files)
        file_operations = make_op_details(files, has_prefix_files, no_link, soft_links, menu_files, link_type)

        # TODO: discuss with @mcg1969
        # run pre-link script
        # if not run_script(source_dir, dist, 'pre-link', prefix):
        #     raise LinkError('Error: pre-link failed: %s' % dist)

        execute_file_operations(extracted_package_directory, prefix, leaf_directories, file_operations)

        # Step 5. Run post-link script
        if not run_script(prefix, dist, 'post-link'):
            raise LinkError("Error: post-link failed for: %s" % dist)

        # Step 6. Create package's prefix/conda-meta file
        create_meta(prefix, dist, info_dir, meta_dict)




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
    build_number = dist.build_number()
    env[str('ROOT_PREFIX')] = sys.prefix
    env[str('PREFIX')] = str(env_prefix or prefix)
    env[str('PKG_NAME')] = name
    env[str('PKG_VERSION')] = version
    env[str('PKG_BUILDNUM')] = build_number
    if action == 'pre-link':
        env[str('SOURCE_DIR')] = str(prefix)
    try:
        subprocess.check_call(args, env=env)
    except subprocess.CalledProcessError:
        return False
    return True

