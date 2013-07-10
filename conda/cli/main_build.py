# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

help = "Build a package from a (conda) recipe. (ADVANCED)"
descr = help + """  For examples of recipes, see:
https://github.com/ContinuumIO/conda-recipes"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('build', description=descr, help=help)

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
    import conda.builder.source as source
    from conda.builder.metadata import MetaData

    for arg in args.recipe:
        if isfile(arg):
            recipe_dir = tempfile.mkdtemp()
            t = tarfile.open(arg, 'r:*')
            t.extractall(path=recipe_dir)
            t.close()
            need_cleanup = True
        else:
            recipe_dir = abspath(arg)
            need_cleanup = False

        if not isdir(recipe_dir):
            sys.exit("Error: no such directory: %s" % recipe_dir)

        m = MetaData(recipe_dir)
        if args.test:
            build.test(m)
        elif args.source:
            source.provide(m.path, m.get_section('source'))
            print 'Source tree in:', source.get_dir()
        else:
            build.build(m)

        if need_cleanup:
            shutil.rmtree(recipe_dir)

        print """\
# If you want to upload this package to binstar.org, type:
#
# $ binstar upload %s
""" % build.bldpkg_path(m)
