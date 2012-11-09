
from config import config


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'info',
        description     = "Display information about current Anaconda install.",
        help            = "Display information about current Anaconda install.",
    )
    p.set_defaults(func=execute)


def execute(args):

    conf = config()

    print
    print "Current Anaconda install:"
    print conf
    print

