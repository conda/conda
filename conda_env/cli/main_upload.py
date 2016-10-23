import textwrap
from argparse import RawDescriptionHelpFormatter
from conda.cli import common
from .. import exceptions
from ..env import from_file
from ..utils.uploader import is_installed, Uploader


description = """
Upload an environment to anaconda.org
"""

example = """
examples:
    conda env upload
    conda env upload project
    conda env upload --file=/path/to/environment.yml
    conda env upload --file=/path/to/environment.yml project
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
        default='Environment file'
    )
    p.add_argument(
        '-q', '--quiet',
        default=False,
        action='store_true'
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

    if args.old_name:
        print("`--name` is deprecated. Use:\n"
              "  conda env upload {}".format(args.old_name))

    try:
        summary = args.summary or env.summary
    except AttributeError:
        summary = None

    try:
        name = args.name or args.old_name or env.name
    except AttributeError:
        msg = """An environment name is required.\n
                 You can specify on the command line as in:
                 \tconda env upload name
                 or you can add a name property to your {} file.""".lstrip().format(args.file)
        raise exceptions.CondaEnvRuntimeError(msg)

    uploader = Uploader(name, args.file, summary=summary, env_data=dict(env.to_dict()))

    if uploader.authorized():
        info = uploader.upload()
        url = info.get('url', 'anaconda.org')
        print("Your environment file has been uploaded to {}".format(url))
    else:
        msg = "\n".join(["You are not authorized to upload a package into Anaconda.org",
                         "Verify that you are logged in anaconda.org with:",
                         "    anaconda login\n"])
        raise exceptions.CondaEnvRuntimeError(msg)

    print("Done.")
