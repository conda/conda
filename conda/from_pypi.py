from __future__ import print_function, division, absolute_import

import sys
import subprocess
from os.path import isfile, join

from conda.resolve import MatchSpec, Resolve
from conda.builder import build, metadata
from conda import config


def pip_args(prefix):
    """
    return the arguments required to invoke pip (in prefix), or None if pip
    in not installed
    """
    if sys.platform == 'win32':
        pip_path = join(prefix, 'Scripts', 'pip-script.py')
        py_path = join(prefix, 'python.exe')
    else:
        pip_path = join(prefix, 'bin', 'pip')
        py_path = join(prefix, 'bin', 'python')
    if isfile(pip_path) and isfile(py_path):
        return [py_path, pip_path]
    else:
        return None


def configure_and_call_function(args, message):
    from conda.cli import conda_argparse
    from conda.cli import main_skeleton
    from conda.cli import main_build
    from conda.cli import main_install

    p = conda_argparse.ArgumentParser()
    sub_parsers = p.add_subparsers(
        metavar = 'command',
        dest = 'cmd',
    )
    eval('main_%s' % args[0]).configure_parser(sub_parsers)
    args = p.parse_args(args=args)
    try:
        args.func(args, p)
    except Exception as e:
        print("Unable to %s.  Error: %s" % (message, e))


def create_recipe(spec):
    rootdir = config.root_dir
    direc = join(rootdir, 'conda-recipes')
    args = ['skeleton', 'pypi', spec, '--no-prompt', '--output-dir', direc]
    configure_and_call_function(args, "create recipe")
    # conda skeleton pypi spec --no-prompt --output-dir root/conda-recipes/spec
    return join(direc, spec.lower())


def build_package(prefix, recipedir):
    args = ['build', recipedir, '--no-test', '--build-recipe']
    if config.binstar_upload is None:
        args.append('--no-binstar-upload')
    configure_and_call_function(args, "build recipe")
    pkgname = build.bldpkg_path(metadata.MetaData(recipedir))
    # conda build recipedir --no-binstar-upload --no-test --build-recipe
    return pkgname


def install_package(prefix, pkgname):
    args = ['install', pkgname, "--no-pip"]
    configure_and_call_function(args, "install package")
    # conda install pkgname


def install_from_pypi(prefix, index, specs):
    r = Resolve(index)
    for_conda = []
    for s in specs:
        try:
            next(r.find_matches(MatchSpec(s)))
        except StopIteration:
            print("Conda package not available for %s, attempting to create "
                  "and install conda package from pypi" % s)
            recipedir = create_recipe(s)
            pkgname = build_package(prefix, recipedir)
            install_package(prefix, pkgname)
        else:
            for_conda.append(s)
    return for_conda


def pip_install(prefix, s):
    # It would be great if conda list could show pip installed packages too
    # We may need to update something after install
    # Also conda remove should uninstall pip-installed packages
    # FIXME: we need to make sure we are running in the correct environment
    args = pip_args(prefix)
    if args is None:
        print("pip is not installed (use conda install pip in env: %s)" %
              prefix)
        return
    args.extend(['install', s])
    if subprocess.call(args) != 0:
        print("Could not install '%s' using pip" % s)


def install_with_pip(prefix, index, specs):
    r = Resolve(index)
    for_conda = []

    try:
        next(r.find_matches(MatchSpec('pip')))
    except StopIteration:
        print("Pip not found, running `conda install pip` ...")
        try:
            install_package(prefix, 'pip')
        except Exception as e:
            print("Could not install pip --- continuing...")
            return specs

    for s in specs:
        try:
            next(r.find_matches(MatchSpec(s)))
        except StopIteration:
            if s == 'pip':
                for_conda.append(s)
                continue
            print("Conda package not available for %s, attempting to install "
                  "via pip" % s)
            pip_install(prefix, s)
        else:
            for_conda.append(s)
    return for_conda
