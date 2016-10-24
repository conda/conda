# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re

from conda.common.disk import yield_lines
from logging import getLogger
from os.path import join, isdir, dirname, islink

log = getLogger(__name__)







def link(prefix, dist, linktype=LINK_HARD, index=None):
    """
    Set up a package in a specified (environment) prefix.  We assume that
    the package has been extracted (using extract() above).
    """
    log.debug("linking package %s with link type %s", dist, linktype)
    index = index or {}
    source_dir = is_extracted(dist)
    assert source_dir is not None
    pkgs_dir = dirname(source_dir)
    log.debug('pkgs_dir=%r, prefix=%r, dist=%r, linktype=%r' %
              (pkgs_dir, prefix, dist, linktype))

    if not run_script(source_dir, dist, 'pre-link', prefix):
        raise LinkError('Error: pre-link failed: %s' % dist)

    info_dir = join(source_dir, 'info')
    files = list(yield_lines(join(info_dir, 'files')))
    has_prefix_files = read_has_prefix(join(info_dir, 'has_prefix'))
    no_link = read_no_link(info_dir)

    # for the lock issue
    # may run into lock if prefix not exist
    if not isdir(prefix):
        os.makedirs(prefix)

    with DirectoryLock(prefix), FileLock(source_dir):
        meta_dict = index.get(dist + '.tar.bz2', {})
        if meta_dict.get('noarch'):
            link_noarch(prefix, meta_dict, source_dir, dist)
        else:
            for filepath in files:
                src = join(source_dir, filepath)
                dst = join(prefix, filepath)
                dst_dir = dirname(dst)
                if not isdir(dst_dir):
                    os.makedirs(dst_dir)
                if os.path.exists(dst):
                    log.info("file exists, but clobbering: %r" % dst)
                    rm_rf(dst)
                lt = linktype
                if filepath in has_prefix_files or filepath in no_link or islink(src):
                    lt = LINK_COPY

                try:
                    if not meta_dict.get('noarch'):
                        _link(src, dst, lt)
                except OSError as e:
                    raise CondaOSError('failed to link (src=%r, dst=%r, type=%r, error=%r)' %
                                       (src, dst, lt, e))

        for filepath in sorted(has_prefix_files):
            placeholder, mode = has_prefix_files[filepath]
            try:
                update_prefix(join(prefix, filepath), prefix, placeholder, mode)
            except _PaddingError:
                raise PaddingError(dist, placeholder, len(placeholder))

        # make sure that the child environment behaves like the parent,
        #    wrt user/system install on win
        # This is critical for doing shortcuts correctly
        if on_win:
            nonadmin = join(sys.prefix, ".nonadmin")
            if isfile(nonadmin):
                open(join(prefix, ".nonadmin"), 'w').close()

        if context.shortcuts:
            mk_menus(prefix, files, remove=False)

        if not run_script(prefix, dist, 'post-link'):
            raise LinkError("Error: post-link failed for: %s" % dist)

        meta_dict['url'] = read_url(dist)
        alt_files_path = join(prefix, 'conda-meta', dist2filename(dist, '.files'))
        if isfile(alt_files_path):
            # alt_files_path is a hack for noarch
            meta_dict['files'] = list(yield_lines(alt_files_path))
        else:
            meta_dict['files'] = files
        meta_dict['link'] = Link(source=source_dir, type=link_name_map.get(linktype))
        if 'icon' in meta_dict:
            meta_dict['icondata'] = read_icondata(source_dir)

        create_meta(prefix, dist, info_dir, meta_dict)


def unlink(prefix, dist):
    """
    Remove a package from the specified environment, it is an error if the
    package does not exist in the prefix.
    """
    with DirectoryLock(prefix):
        log.debug("unlinking package %s", dist)
        run_script(prefix, dist, 'pre-unlink')

        meta = load_meta(prefix, dist)
        # Always try to run this - it should not throw errors where menus do not exist
        mk_menus(prefix, meta['files'], remove=True)
        dst_dirs1 = set()

        for f in meta['files']:
            dst = join(prefix, f)
            dst_dirs1.add(dirname(dst))
            rm_rf(dst)

        # remove the meta-file last
        delete_linked_data(prefix, dist, delete=True)

        dst_dirs2 = set()
        for path in dst_dirs1:
            while len(path) > len(prefix):
                dst_dirs2.add(path)
                path = dirname(path)
        # in case there is nothing left
        dst_dirs2.add(join(prefix, 'conda-meta'))
        dst_dirs2.add(prefix)

        noarch = meta.get("noarch")
        if noarch:
            get_noarch_cls(noarch)().unlink(prefix, dist)

        # remove empty directories
        for path in sorted(dst_dirs2, key=len, reverse=True):
            if isdir(path) and not os.listdir(path):
                rm_rf(path)

        alt_files_path = join(prefix, 'conda-meta', dist2filename(dist, '.files'))
        if isfile(alt_files_path):
            rm_rf(alt_files_path)


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
            makedirs(join(prefix, d))

        # Step 2. Do the actual file linking
        # Step 3. Replace prefix placeholder within all necessary files
        # Step 4. Make shortcuts on Windows
        for op in file_operations:
            file_path, link_type, prefix_placeholder, file_mode, is_menu_file = op
            source_path = join(extracted_package_directory, file_path)
            destination_path = join(prefix, file_path)
            try:
                _link(source_path, destination_path, link_type)
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
            nonadmin = join(sys.prefix, ".nonadmin")
            if isfile(nonadmin):
                open(join(prefix, ".nonadmin"), 'w').close()




class PackageInstaller(object):

    def __init__(self, prefix, extracted_package_directory):

        # directories to create

        # source_paths, destination_paths, link_types, prefix_to_replace

        # destination_paths, prefix_to_replace



        self.prefix = prefix
        self.extracted_package_directory = extracted_package_directory

    def link(self, link_type='LINK_HARD'):
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



        # # for the lock issue
        # # may run into lock if prefix not exist
        # if not isdir(prefix):
        #     os.makedirs(prefix)
        assert isdir(self.prefix)



            # Step 5. Run post-link script
            if not run_script(prefix, dist, 'post-link'):
                raise LinkError("Error: post-link failed for: %s" % dist)

            # Step 6. Create package's prefix/conda-meta file
            create_meta(prefix, dist, info_dir, meta_dict)




            # meta_dict = index.get(dist + '.tar.bz2', {})
            # if meta_dict.get('noarch'):
            #     link_noarch(prefix, meta_dict, source_dir, dist)
            # else:
            #     for filepath in files:
            #         src = join(source_dir, filepath)
            #         dst = join(prefix, filepath)
            #         dst_dir = dirname(dst)
            #         if not isdir(dst_dir):
            #             os.makedirs(dst_dir)
            #         if os.path.exists(dst):
            #             log.info("file exists, but clobbering: %r" % dst)
            #             rm_rf(dst)
            #         lt = linktype
            #         if filepath in has_prefix_files or filepath in no_link or islink(src):
            #             lt = LINK_COPY
            #
            #         try:
            #             if not meta_dict.get('noarch'):
            #                 _link(src, dst, lt)
            #         except OSError as e:
            #             raise CondaOSError('failed to link (src=%r, dst=%r, type=%r, error=%r)' %
            #                                (src, dst, lt, e))

            # replace prefix placeholder within all necessary files
            for filepath in sorted(has_prefix_files):
                placeholder, mode = has_prefix_files[filepath]
                try:
                    update_prefix(join(prefix, filepath), prefix, placeholder, mode)
                except _PaddingError:
                    raise PaddingError(dist, placeholder, len(placeholder))

            # make shortcuts on Windows

                if context.shortcuts:
                    mk_menus(prefix, files, remove=False)

            # run post-link script
            if not run_script(prefix, dist, 'post-link'):
                raise LinkError("Error: post-link failed for: %s" % dist)

            # # create package's prefix/conda-meta file
            # meta_dict['url'] = read_url(dist)
            # alt_files_path = join(prefix, 'conda-meta', dist2filename(dist, '.files'))
            # if isfile(alt_files_path):
            #     # alt_files_path is a hack for noarch
            #     meta_dict['files'] = list(yield_lines(alt_files_path))
            # else:
            #     meta_dict['files'] = files
            # meta_dict['link'] = Link(source=source_dir, type=link_name_map.get(linktype))
            # if 'icon' in meta_dict:
            #     meta_dict['icondata'] = read_icondata(source_dir)
            #
            # create_meta(prefix, dist, info_dir, meta_dict)
