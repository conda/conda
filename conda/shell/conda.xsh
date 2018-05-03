from argparse import ArgumentParser
import os
import sys

if '_CONDA_EXE' not in locals():
    _CONDA_EXE = "python -m conda"  # development mode

_REACTIVATE_COMMANDS = ('install', 'update', 'upgrade', 'remove', 'uninstall')


def _parse_args(args=None):
    p = ArgumentParser(add_help=False)
    p.add_argument('command')
    ns, _ = p.parse_known_args(args)
    if ns.command == 'activate':
        p.add_argument('env_name_or_prefix', default='base')
    elif ns.command in _REACTIVATE_COMMANDS:
        p.add_argument('-n', '--name')
        p.add_argument('-p', '--prefix')
    parsed_args, _ = p.parse_known_args(args)
    return parsed_args


def _raise_pipeline_error(pipeline):
    stdout = pipeline.out
    stderr = pipeline.err
    if pipeline.returncode != 0:
        message = ("exited with %s\nstdout: %s\nstderr: %s\n"
                   "" % (pipeline.returncode, stdout, stderr))
        raise RuntimeError(message)
    return stdout.strip()


def _conda_activate_handler(env_name_or_prefix):
    pipeline = !(@(_CONDA_EXE) shell.xonsh activate @(env_name_or_prefix))
    stdout = _raise_pipeline_error(pipeline)
    source @(stdout)
    os.unlink(stdout)


def _conda_deactivate_handler():
    pipeline = !(@(_CONDA_EXE) shell.xonsh deactivate)
    stdout = _raise_pipeline_error(pipeline)
    source @(stdout)
    os.unlink(stdout)


def _conda_passthrough_handler(args):
    pipeline = ![@(_CONDA_EXE) @(' '.join(args))]
    _raise_pipeline_error(pipeline)


def _conda_reactivate_handler(args, name_or_prefix_given):
    pipeline = ![@(_CONDA_EXE) @(' '.join(args))]
    _raise_pipeline_error(pipeline)

    if not name_or_prefix_given:
        pipeline = !(@(_CONDA_EXE) shell.xonsh reactivate)
        stdout = _raise_pipeline_error(pipeline)
        source @(stdout)
        os.unlink(stdout)


def _conda_main(args=None):
    parsed_args = _parse_args(args)
    if parsed_args.command == 'activate':
        _conda_activate_handler(parsed_args.env_name_or_prefix)
    elif parsed_args.command == 'deactivate':
        _conda_deactivate_handler()
    elif parsed_args.command in _REACTIVATE_COMMANDS:
        name_or_prefix_given = bool(parsed_args.name or parsed_args.prefix)
        _conda_reactivate_handler(args, name_or_prefix_given)
    else:
        _conda_passthrough_handler(args)


if 'CONDA_SHLVL' not in ${...}:
    $CONDA_SHLVL = '0'

aliases['conda'] = _conda_main
