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
https://github.com/ContinuumIO/conda-recipes"""

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


def execute(args, parser):
    import sys
    import os
    import shutil
    import tarfile
    import tempfile
    from os.path import abspath, isdir, isfile, join

    from conda.lock import Locked
    import conda.builder.build as build
    import conda.builder.source as source
    from conda.builder.config import croot
    from conda.builder.metadata import MetaData

    with Locked(croot):
        # get once all recipes
        all_recipies = {}
        for root, dirs, files in os.walk(config.conda_recipes_dir):
            for any_dir in dirs:
                any_dir_path = os.path.join(root, any_dir)
                if os.path.isfile(os.path.join(any_dir_path, "meta.yaml")):
                    if any_dir not in all_recipies:
                        all_recipies[any_dir] = any_dir_path
                    else:
                        raise Exception("\nRecipes must have unique names: "
                        "Same recipe name: <%s> exist at: \n"
                        "<%s>\n"
                        "<%s>\n" % (any_dir, any_dir_path, all_recipies[any_dir]))
                        
        for arg in args.recipe:
            if isfile(arg) and arg.endswith(('.tar', '.tar.gz', '.tgz', '.tar.bz2')):
                recipe_dir = tempfile.mkdtemp()
                t = tarfile.open(arg, 'r:*')
                t.extractall(path=recipe_dir)
                t.close()
                need_cleanup = True
            else:
                recipe_dir = abspath(arg)
                need_cleanup = False

            if not isdir(recipe_dir):
                # See if it's a spec and the directory is in conda-recipes
                if arg not in all_recipies:
                    # if --use-pypi and recipe_dir is a spec
                    # try to create the skeleton
                    if args.pypi:
                        from conda.from_pypi import create_recipe
                        try:
                            recipe_dir = create_recipe(arg)
                        except:
                            recipe_dir = abspath(arg)
                    else:
                        sys.exit("Error: did not find any recipes for: "
                        "<%s>: Recipes Root Dir: "
                        "<%s> " % (arg, config.conda_recipes_dir))
                else:
                    recipe_dir = abspath(all_recipies[arg])
                    need_cleanup = False
                    
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
                build.test(m, pypi=args.pypi)
            elif args.source:
                source.provide(m.path, m.get_section('source'))
                print('Source tree in:', source.get_dir())
            else:
                build.build(m, pypi=args.pypi)
                if not args.notest:
                    build.test(m, pypi=args.pypi)

            if need_cleanup:
                shutil.rmtree(recipe_dir)

            # check install now
            install_choice = "y"
            if not config.always_yes:
                while True:
                    # raw_input has a bug and prints to stderr, 
                    # not desirable
                    sys.stdout.write("\nDo you want to install this "
                        "package now?\ny=yes,n=no,e=(extract implies "
                        "no checks) ([y]/n/e)?: ")
                    sys.stdout.flush()
                    try:
                        install_choice = sys.stdin.readline().strip().lower()
                        if install_choice:
                            if install_choice not in ('y', 'n', 'e'):
                                print("Invalid choice: %s. must be one "
                                    "of: y/n/e=(extract implies "
                                    "no checks)" % install_choice)
                            else:
                                sys.stdout.write("\n")
                                sys.stdout.flush()
                                break
                        else: 
                            install_choice = "y"
                            break
                    except KeyboardInterrupt:
                        sys.exit("\nOperation aborted.  Exiting.") 

            if install_choice == "y":
                import subprocess
                from conda.builder.external import find_executable
                from conda.utils import url_path
                
                temp_conda = find_executable('conda')
                if temp_conda is None:
                    sys.exit('''
                        Error: cannot locate conda (required for install)
                        # Try:
                        # $ conda install %s
                        ''' % m.name())

                temp_args = [temp_conda, 'install',
                    '--channel', url_path(config.conda_repo_dir), 
                    '--no-pip',  m.name()]
                subprocess.call(temp_args)
                print()
            elif install_choice == "e":
                from conda.misc import install_local_packages

                temp_prefix = config.default_prefix
                install_local_packages(temp_prefix, 
                    [build.bldpkg_path(m)], verbose=True)
                print()
                
                
            handle_binstar_upload(build.bldpkg_path(m), args)
