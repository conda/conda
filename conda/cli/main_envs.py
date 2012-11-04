
from argparse import ArgumentDefaultsHelpFormatter

from config import config


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'envs',
        description     = "List all known Anaconda environments.",
        help            = "List all known Anaconda environments.",
        formatter_class = ArgumentDefaultsHelpFormatter,
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    conf = config()

    envs = conf.environments

    print "Known Anaconda environments:"
    print

    for env in envs:
        print "    %s" % env.prefix
    print

