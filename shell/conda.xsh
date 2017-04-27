from argparse import ArgumentParser
import os
import sys


def _conda_command_parser(args=None):
    p = ArgumentParser(add_help=False)
    p.add_argument('command')
    ns, unknown = p.parse_known_args(args)
    if ns.command == 'activate':
        p.add_argument('env_name_or_prefix', default='root')
    elif ns.command in ('install', 'update', 'remove', 'uninstall'):
        p.add_argument('-n', '--name')
        p.add_argument('-p', '--prefix')
    return p


def _raise_pipeline_error(pipeline):
    stdout = pipeline.out
    stderr = pipeline.err
    if pipeline.returncode != 0:
        message = ("exited with %s\nstdout: %s\nstderr: %s\n"
                   "" % (pipeline.returncode, stdout, stderr))
        raise RuntimeError(message)
    return stdout.strip()


def _conda_activate_handler(env_name_or_prefix):
    pipeline = !(python -m conda shell.activate xonsh @(env_name_or_prefix))
    stdout = _raise_pipeline_error(pipeline)
    source @(stdout)
    os.unlink(stdout)


def _conda_deactivate_handler():
    pipeline = !(python -m conda shell.deactivate xonsh)
    stdout = _raise_pipeline_error(pipeline)
    source @(stdout)
    os.unlink(stdout)


def _conda_passthrough_handler(args):
    pipeline = ![python -m conda @(' '.join(args))]
    _raise_pipeline_error(pipeline)


def _conda_reactivate_handler(args):
    pipeline = ![python -m conda @(' '.join(args))]
    _raise_pipeline_error(pipeline)

    pipeline = !(python -m conda shell.reactivate xonsh)
    stdout = _raise_pipeline_error(pipeline)
    source @(stdout)
    os.unlink(stdout)


def _conda_main(args=None):
    p = _conda_command_parser(args)
    ns, unknown = p.parse_known_args(args)
    if ns.command == 'activate':
        _conda_activate_handler(ns.env_name_or_prefix)
    elif ns.command == 'deactivate':
        _conda_deactivate_handler()
    elif ns.command in ('install', 'update', 'remove', 'uninstall'):
        _conda_reactivate_handler(args)
    else:
        _conda_passthrough_handler(args)


if 'CONDA_SHLVL' not in ${...}:
    $CONDA_SHLVL = '0'

aliases['conda'] = _conda_main
