# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import


descr = ("Build skeleton recipes for packages from popular package hosting "
         "sites. (ADVANCED)")


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('skeleton', description=descr, help=descr)

    repos = p.add_subparsers(
        dest="repo"
    )

    pypi = repos.add_parser(
        "pypi",
        help="Create recipes from packages on PyPI",
        )
    pypi.add_argument(
        "packages",
        action = "store",
        nargs = '+',
        help = "PyPi packages to create recipe skeletons for",
        )
    pypi.add_argument(
        "--output-dir",
        action = "store",
        nargs = 1,
        help = "Directory to write recipes to",
        default = ".",
        )
    pypi.add_argument(
        "--version",
        action = "store",
        nargs = 1,
        help = "Version to use. Applies to all packages",
        )
    pypi.add_argument(
        "--all-urls",
        action = "store_true",
        help = """Look at all urls, not just source urls. Use this if it can't
        find the right url.""",
        )
    pypi.add_argument(
        "--pypi-url",
        action = "store",
        nargs=1,
        default='http://pypi.python.org/pypi',
        help = "Url to use for PyPI",
        )
    pypi.add_argument(
        "--no-download",
        action = "store_false",
        dest = "download",
        default=True,
        help="""Don't download the package. This will keep the recipe from
        finding the right dependencies and entry points if the package uses
        distribute.  WARNING: The default option downloads and runs the
        package's setup.py script."""
        )
    pypi.add_argument(
        "--no-prompt",
        action="store_true",
        default=False,
        dest="noprompt",
        help="""Don't prompt the user on ambiguous choices.  Instead, make the
        best possible choice and continue."""
        )
    p.set_defaults(func=execute)


def execute(args, parser):
    import conda.builder.pypi as pypi

    if args.repo == "pypi":
        pypi.main(args, parser)
