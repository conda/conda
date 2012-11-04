
from argparse import ArgumentDefaultsHelpFormatter

from config import config


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'info',
        description     = "Display information about current Anaconda install.",
        help            = "Display information about current Anaconda install.",
        formatter_class = ArgumentDefaultsHelpFormatter,
    )
    p.set_defaults(func=execute)


def execute(args, parser):

    conf = config()

    print
    print "Current Anaconda install:"
    print conf
    print

