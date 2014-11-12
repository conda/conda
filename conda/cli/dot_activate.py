from __future__ import absolute_import, print_function
import sys
import os

# TODO Move this to its new home once its found
from conda.cli.activate import binpath_from_arg


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('..activate')
    p.add_argument(
        'environment'
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    binpath = binpath_from_arg(args.environment)
    paths = [binpath]
    sys.stderr.write("prepending %s to PATH\n" % binpath)

    for path in os.getenv('PATH').split(os.pathsep):
        if path != binpath:
            paths.append(path)
    print(os.pathsep.join(paths))
