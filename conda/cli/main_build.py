# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import subprocess

from conda.cli import common
import conda.config as config

help = "Build a package from a (conda) recipe. (ADVANCED)"

descr = help + """  For examples of recipes, see:
https://github.com/ContinuumIO/conda-recipes"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('build', description=descr, help=help)

    p.add_argument(
        '-c', "--check",
        action = "store_true",
        help   = "only check (validate) the recipe",
    )
    p.add_argument(
        "--no-binstar-upload",
        action = "store_false",
        help = "do not ask to upload the package to binstar",
        dest='binstar_upload',
        default=config.binstar_upload,
    )
    p.add_argument(
        "--output",
        action = "store_true",
        help = "output the conda package filename which would have been "
               "created and exit",
    )
    p.add_argument(
        '-s', "--source",
        action  = "store_true",
        help    = "only obtain the source (but don't build)",
    )
    p.add_argument(
        '-t', "--test",
        action  = "store_true",
        help    = "test package (assumes package is already build)",
    )
    p.add_argument('recipe',
                   action="store",
                   metavar='PATH',
                   nargs='+',
                   help="path to recipe directory",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import sys
    import shutil
    import tarfile
    import tempfile
    from os.path import abspath, isdir, isfile

    import conda.builder.build as build
    from conda.builder.external import find_executable
    from conda.builder.config import croot
    import conda.builder.source as source
    from conda.builder.metadata import MetaData
    from conda.lock import Locked

    with Locked(croot):
        for arg in args.recipe:
            if isfile(arg):
                if arg.endswith(('.tar', '.tar.gz', '.tgz', '.tar.bz2')):
                    recipe_dir = tempfile.mkdtemp()
                    t = tarfile.open(arg, 'r:*')
                    t.extractall(path=recipe_dir)
                    t.close()
                    need_cleanup = True
                else:
                    print("Ignoring: %s" % arg)
                    continue
            else:
                recipe_dir = abspath(arg)
                need_cleanup = False

            if not isdir(recipe_dir):
                sys.exit("Error: no such directory: %s" % recipe_dir)

            m = MetaData(recipe_dir)
            if args.check and len(args.recipe) > 1:
                print(m.path)
            m.check_fields()
            if args.check:
                continue
            if args.output:
                print(build.bldpkg_path(m))
                continue
            elif args.test:
                build.test(m)
            elif args.source:
                source.provide(m.path, m.get_section('source'))
                print('Source tree in:', source.get_dir())
            else:
                build.build(m)

            if need_cleanup:
                shutil.rmtree(recipe_dir)

            if args.binstar_upload is None:
                args.yes = False
                args.dry_run = False
                upload = common.confirm_yn(
                    args,
                    message="Do you want to upload this "
                    "package to binstar", default='yes', exit_no=False)
            else:
                upload = args.binstar_upload

            if not upload:
                print("""\
# If you want to upload this package to binstar.org later, type:
#
# $ binstar upload %s
""" % build.bldpkg_path(m))
                continue

            binstar = find_executable('binstar')
            if binstar is None:
                sys.exit('''
Error: cannot locate binstar (required for upload)
# Try:
# $ conda install binstar
''')
            subprocess.call([binstar, 'upload', build.bldpkg_path(m)])
