# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
import os
import types

from ._vendor import click

from .config import envs_dirs

HOME = os.environ['HOME']
PWD = os.environ['PWD']
assert os.getcwd() == PWD


def expand(path):
    return os.path.join(PWD, os.path.normpath(os.path.expanduser(os.path.expandvars(path))))


def take_first(maybe_iterable):
    if isinstance(maybe_iterable, types.StringTypes):
        return maybe_iterable
    elif hasattr(maybe_iterable, '__iter__'):
        if len(maybe_iterable) > 0:
            return maybe_iterable[0]
        else:
            return None
    else:
        return maybe_iterable


@click.group()
def cli():
    pass


def is_env_location(path):
    path = expand(path)
    cm = os.path.join(path, 'conda-meta')
    return os.path.isdir(path) and os.path.isdir(cm)


def find_dot_conda_dir(path):
    if path in (HOME, '/'):
        return None
    elif os.path.join(path, '.conda'):
        return path
    else:
        return find_dot_conda_dir(os.path.dirname(path))


def has_env_yml(path):
    yml_path = os.path.join(path, '.condaenv.yml')
    return os.path.isfile(yml_path)


def _find_env_location(given='.'):
    """
    Args:
        given:

    Returns:


    """
    # Step 1: assume given is a path
    given_as_path = expand(given)
    if os.path.exists(given_as_path) and is_env_location(given_as_path):
        return given_as_path

    # Step 2: look up directory tree for .conda directory
    #         - does that directory have a .condaenv.yml?
    dot_conda_dir = find_dot_conda_dir(PWD)
    if dot_conda_dir and has_env_yml(dot_conda_dir):
        if given == '.':
            basename = os.path.basename(dot_conda_dir)
            env_location = os.path.join(dot_conda_dir, '.conda', basename)
        else:
            env_location = os.path.join(dot_conda_dir, '.conda', given)
        if is_env_location(env_location):
            return env_location

    # Step 3: look for a named environment
    for env_dir in envs_dirs:
        named_path = os.path.join(env_dir, given)
        if is_env_location(named_path):
            return named_path


def get_env_path(given=None):
    location = _find_env_location(given)
    if location:
        return os.path.join(location, 'bin')


@cli.command()
@click.argument('given', nargs=-1)
def find_env_location(given):
    result = _find_env_location(take_first(given) or '.')
    click.echo(result)
