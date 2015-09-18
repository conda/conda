# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common


descr = "Low-level conda package utility. (EXPERIMENTAL)"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'package',
        description=descr,
        help=descr,
    )
    common.add_parser_prefix(p)
    p.add_argument(
        '-w', "--which",
        metavar="PATH",
        nargs='+',
        action="store",
        help="Given some PATH print which conda package the file came from.",
    )
    p.add_argument(
        '-L', "--ls-files",
        metavar='PKG-NAME',
        action="store",
        help="List all files belonging to specified package.",
    )
    p.add_argument(
        '-r', "--reset",
        action="store_true",
        help="Remove all untracked files and exit.",
    )
    p.add_argument(
        '-u', "--untracked",
        action="store_true",
        help="Display all untracked files and exit.",
    )
    p.add_argument(
        "--pkg-name",
        action="store",
        default="unknown",
        help="Package name of the created package.",
    )
    p.add_argument(
        "--pkg-version",
        action="store",
        default="0.0",
        help="Package version of the created package.",
    )
    p.add_argument(
        "--pkg-build",
        action="store",
        default=0,
        help="Package build number of the created package.",
    )
    p.set_defaults(func=execute)

def list_package_files(pkg_name=None):
    import os
    import re
    import conda.config as config
    from conda.misc import walk_prefix

    pkgs_dirs = config.pkgs_dirs[0]
    all_dir_names = []
    pattern = re.compile(pkg_name, re.I)

    print('\nINFO: The location for available packages: %s' % (pkgs_dirs))

    for dir in os.listdir(pkgs_dirs):
        ignore_dirs = [ '_cache-0.0-x0', 'cache' ]

        if dir in ignore_dirs:
            continue

        if not os.path.isfile(pkgs_dirs+"/"+dir):
            match = pattern.match(dir)

            if match:
                all_dir_names.append(dir)

    num_of_all_dir_names = len(all_dir_names)
    dir_num_width = len(str(num_of_all_dir_names))

    if num_of_all_dir_names == 0:
        print("\n\tWARN: There is NO '%s' package.\n" % (pkg_name))
        return 1
    elif num_of_all_dir_names >= 2:
        print("\n\tWARN: Ambiguous package name ('%s'), choose one name from below list:\n" % (pkg_name))

        num = 0
        for dir in all_dir_names:
            num += 1
            print("\t[ {num:>{width}} / {total} ]: {dir}".format(num=num, width=dir_num_width, total=num_of_all_dir_names, dir=dir))
        print("")
        return 1

    full_pkg_name = all_dir_names[0]

    print("INFO: All files belonging to '%s' package:\n" % (full_pkg_name))

    pkg_dir = pkgs_dirs+"/"+full_pkg_name

    ret = walk_prefix(pkg_dir, ignore_predefined_files=False)

    for item in ret:
        print(pkg_dir+"/"+item)

def execute(args, parser):
    import sys

    from conda.misc import untracked
    from conda.packup import make_tarbz2, remove


    prefix = common.get_prefix(args)

    if args.which:
        from conda.misc import which_package

        for path in args.which:
            for dist in which_package(path):
                print('%-50s  %s' % (path, dist))
        return

    if args.ls_files:
        if list_package_files(args.ls_files) == 1:
            sys.exit(1)
        else:
            return

    print('# prefix:', prefix)

    if args.reset:
        remove(prefix, untracked(prefix))
        return

    if args.untracked:
        files = sorted(untracked(prefix))
        print('# untracked files: %d' % len(files))
        for fn in files:
            print(fn)
        return

    make_tarbz2(prefix,
                name = args.pkg_name.lower(),
                version = args.pkg_version,
                build_number = int(args.pkg_build))
