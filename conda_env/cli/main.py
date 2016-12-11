from __future__ import print_function, division, absolute_import

from logging import getLogger, CRITICAL

import os
import sys

try:
    from conda.exceptions import conda_exception_handler
except ImportError as e:
    if 'CONDA_DEFAULT_ENV' in os.environ:
        sys.stderr.write("""
There was an error importing conda.

It appears this was caused by installing conda-env into a conda
environment.  Like conda, conda-env needs to be installed into your
root conda/Anaconda environment.

Please deactivate your current environment, then re-install conda-env
using this command:

    conda install -c conda conda-env

If you are seeing this error and have not installed conda-env into an
environment, please open a bug report at:
    https://github.com/conda/conda-env

""".lstrip())
        sys.exit(-1)
    else:
        raise e

from conda.cli.conda_argparse import ArgumentParser

from . import main_attach
from . import main_create
from . import main_export
from . import main_list
from . import main_remove
from . import main_upload
from . import main_update
from conda.base.context import context

# TODO: This belongs in a helper library somewhere
# Note: This only works with `conda-env` as a sub-command.  If this gets
# merged into conda-env, this needs to be adjusted.
def show_help_on_empty_command():
    if len(sys.argv) == 1:  # sys.argv == ['/path/to/bin/conda-env']
        sys.argv.append('--help')


def create_parser():
    p = ArgumentParser()
    sub_parsers = p.add_subparsers()

    main_attach.configure_parser(sub_parsers)
    main_create.configure_parser(sub_parsers)
    main_export.configure_parser(sub_parsers)
    main_list.configure_parser(sub_parsers)
    main_remove.configure_parser(sub_parsers)
    main_upload.configure_parser(sub_parsers)
    main_update.configure_parser(sub_parsers)

    show_help_on_empty_command()
    return p


def main():
    parser = create_parser()
    args = parser.parse_args()
    context._set_argparse_args(args)
    if getattr(args, 'json', False):
        # # Silence logging info to avoid interfering with JSON output
        # for logger in Logger.manager.loggerDict:
        #     if logger not in ('fetch', 'progress'):
        #         getLogger(logger).setLevel(CRITICAL + 1)
        for logger in ('print', 'dotupdate', 'stdoutlog', 'stderrlog'):
            getLogger(logger).setLevel(CRITICAL + 1)

    return conda_exception_handler(args.func, args, parser)


if __name__ == '__main__':
    sys.exit(main())
