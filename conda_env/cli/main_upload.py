import textwrap
from argparse import RawDescriptionHelpFormatter
from conda.cli import common
from .. import exceptions
from ..env import from_file
from ..utils.uploader import is_installed


description = """
Upload an environment to binstar
"""

example = """
examples:
    conda env upload
    conda env upload project
    conda env upload user/project
    conda env upload --file=/path/to/environment.yml
    conda env upload --file=/path/to/environment.yml user/project
    conda env upload --force
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'upload',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )
    p.add_argument(
        '-n', '--name',
        action='store',
        help='environment definition [Deprecated]',
        default=None,
        dest='old_name'
    )
    p.add_argument(
        '-f', '--file',
        action='store',
        help='environment definition file (default: environment.yml)',
        default='environment.yml',
    )
    p.add_argument(
        '--summary',
        help='Short summary of the environment',
    )
    p.add_argument(
        '--force',
        action='store_true',
        default=False,
        help='Replace existing environment definition'
    )
    p.add_argument(
        '-q', '--quiet',
        default=False,
        action='store_false'
    )
    p.add_argument(
        'name',
        help='environment definition',
        action='store',
        default=None,
        nargs='?'
    )
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):

    """
    * Binstar-cli must be installed (verify) - Raise error if it's not
    -f = False -> Verify environment.yml or environment.yaml
    -f = /path -> isFile?

    -n present -> Show deprecation warning

    [name] -> present
    Authorize binstar
        no-authorized: ask for credentials
        authorized:
            if user/project exists and -f flag, overwrite
            else: show error
            if user/project no-exists -> create and upload
    """

    if not is_installed():
        raise exceptions.NoBinstar()

    try:
        env = from_file(args.file)
    except exceptions.EnvironmentFileNotFound as e:
        msg = 'Unable to locate environment file: %s\n\n' % e.filename
        msg += "\n".join(textwrap.wrap(textwrap.dedent("""
            Please verify that the above file is present and that you have
            permission read the file's contents.  Note, you can specify the
            file to use by explictly adding --file=/path/to/file when calling
            conda env create.""").lstrip()))
        raise exceptions.CondaEnvRuntimeError(msg)

    return env
