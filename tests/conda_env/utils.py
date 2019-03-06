from argparse import ArgumentParser
from contextlib import contextmanager
from tempfile import mkdtemp
from conda._vendor.auxlib.compat import shlex_split_unicode

from conda.gateways.disk.delete import rm_rf

from conda_env.cli.main import do_call as do_call_conda_env
from conda_env.cli.main_create import configure_parser as create_configure_parser
from conda_env.cli.main_update import configure_parser as update_configure_parser
from conda_env.cli.main_export import configure_parser as export_configure_parser


class Commands:
    CREATE = "create"
    UPDATE = "update"
    EXPORT = "export"


parser_config = {
    Commands.CREATE: create_configure_parser,
    Commands.UPDATE: update_configure_parser,
    Commands.EXPORT: export_configure_parser,
}


def escape_for_winpath(p):
    return p.replace('\\', '\\\\')


@contextmanager
def make_temp_envs_dir():
    envs_dir = mkdtemp()
    try:
        yield envs_dir
    finally:
        rm_rf(envs_dir)


def run_command(command, env_name, *arguments):
    p = ArgumentParser()
    sub_parsers = p.add_subparsers(metavar='command', dest='cmd')
    parser_config[command](sub_parsers)

    arguments = list(map(escape_for_winpath, arguments))
    command_line = "{0} -n {1} -f {2}".format(command, env_name, " ".join(arguments))

    args = p.parse_args(shlex_split_unicode(command_line))
    do_call_conda_env(args, p)
