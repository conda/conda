# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys

from conda.cli import common
import conda.config as config



help = "Build a package from a (conda) recipe. (ADVANCED)"

descr = help + """  For examples of recipes, see:
https://github.com/pydata/conda-recipes"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('build', description=descr, help=help)

    p.add_argument(
        '-c', "--check",
        action = "store_true",
        help = "only check (validate) the recipe",
    )
    p.add_argument(
        "--no-binstar-upload",
        action = "store_false",
        help = "do not ask to upload the package to binstar",
        dest = 'binstar_upload',
        default = config.binstar_upload,
    )
    p.add_argument(
        "--output",
        action = "store_true",
        help = "output the conda package filename which would have been "
               "created and exit",
    )
    p.add_argument(
        '-s', "--source",
        action = "store_true",
        help = "only obtain the source (but don't build)",
    )
    p.add_argument(
        '-t', "--test",
        action = "store_true",
        help = "test package (assumes package is already build)",
    )
    p.add_argument(
        'recipe',
        action = "store",
        metavar = 'PATH',
        nargs = '+',
        help = "path to recipe directory",
    )
    p.add_argument(
        '--no-test',
        action='store_true',
        dest='notest',
        help="do not test the package"
    )
    p.add_argument(
        '--build-recipe',
        action='store_true',
        default=False,
        dest='pypi',
        help="Try to build conda package from pypi")
    p.set_defaults(func=execute)


def handle_binstar_upload(path, args):
    import subprocess
    from conda.builder.external import find_executable

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
""" % path)
        return

    binstar = find_executable('binstar')
    if binstar is None:
        sys.exit('''
Error: cannot locate binstar (required for upload)
# Try:
# $ conda install binstar
''')
    print("Uploading to binstar")
    args = [binstar, 'upload', path]
    if config.binstar_personal:
        args += ['--personal']
    subprocess.call(args)


def check_external():
    import os
    import conda.builder.external as external

    if sys.platform.startswith('linux'):
        chrpath = external.find_executable('chrpath')
        if chrpath is None:
            sys.exit("""\
Error:
    Did not find 'chrpath' in: %s
    'chrpath' is necessary for building conda packages on Linux with
    relocatable ELF libraries.  You can install chrpath using apt-get,
    yum or conda.
""" % (os.pathsep.join(external.dir_paths)))


def execute(args, parser):
    import sys
    import shutil
    import tarfile
    import tempfile
    from os.path import abspath, isdir, isfile, join

    from conda.lock import Locked
    import conda.builder.build as build
    import conda.builder.source as source
    from conda.builder.config import croot
    from conda.builder.metadata import MetaData

    check_external()

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
                    print("Ignoring non-recipe: %s" % arg)
                    continue
            else:
                recipe_dir = abspath(arg)
                need_cleanup = False

            if not isdir(recipe_dir):
                # See if it's a spec and the directory is in conda-recipes
                recipe_dir = join(config.root_dir, 'conda-recipes', arg)
                if not isdir(recipe_dir):
                    # if --use-pypi and recipe_dir is a spec
                    # try to create the skeleton
                    if args.pypi:
                        from conda.from_pypi import create_recipe
                        try:
                            recipe_dir = create_recipe(arg)
                        except:
                            recipe_dir = abspath(arg)
                    if not isdir(recipe_dir):
                        sys.exit("Error: no such directory: %s" % recipe_dir)

            m = MetaData(recipe_dir)
            binstar_upload = False
            if args.check and len(args.recipe) > 1:
                print(m.path)
            m.check_fields()
            if args.check:
                continue
            if args.output:
                print(build.bldpkg_path(m))
                continue
            elif args.test:
                build.test(m, pypi=args.pypi)
            elif args.source:
                source.provide(m.path, m.get_section('source'))
                print('Source tree in:', source.get_dir())
            else:
                build.build(m, pypi=args.pypi)
                if not args.notest:
                    build.test(m, pypi=args.pypi)
                binstar_upload = True

            if need_cleanup:
                shutil.rmtree(recipe_dir)

            if binstar_upload:
                handle_binstar_upload(build.bldpkg_path(m), args)
