from __future__ import print_function, division, absolute_import
from conda.resolve import MatchSpec, Resolve
import argparse
import os.path
from conda.builder import build, metadata
from conda import config
import subprocess

def configure_and_call_function(args, message):
    from conda.cli import main_skeleton
    from conda.cli import main_build
    from conda.cli import main_install
    from conda.cli import conda_argparse

    p = conda_argparse.ArgumentParser()
    sub_parsers = p.add_subparsers(
        metavar = 'command',
        dest = 'cmd',
    )
    eval('main_%s'%args[0]).configure_parser(sub_parsers)
    args = p.parse_args(args=args)
    try:
        args.func(args, p)
    except Exception as e:
        print("Unable to %s.  Error: %s" % (message, e))


def create_recipe(spec):
    rootdir = config.root_dir
    direc = os.path.join(rootdir, 'conda-recipes')
    args = ['skeleton','pypi', spec, '--no-prompt','--output-dir', direc]
    configure_and_call_function(args, "create recipe")
    # conda skeleton pypi spec --no-prompt --output-dir root/conda-recipes/spec
    return os.path.join(direc, spec)

def build_package(prefix, recipedir):
    args = ['build', recipedir, '--no-binstar-upload', '--no-test', '--use-pypi']
    configure_and_call_function(args, "build recipe")
    pkgname = build.bldpkg_path(metadata.MetaData(recipedir))
    # conda build recipedir --no-binstar-upload --no-test --use-pypi
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
            r.find_matches(MatchSpec(s)).next()
        except StopIteration:
            print("Conda package not available for %s, attempting to create and install conda package from pypi" % s)
            recipedir = create_recipe(s)
            pkgname = build_package(prefix, recipedir)
            install_package(prefix, pkgname)
        else:
            for_conda.append(s)            
    return for_conda

def pip_install(prefix, s):
    # pip install <s>
    # It would be great if conda list could show pip installed packages too
    #  We may need to update something after install
    # Also conda remove should uninstall pip-installed packages
    # FIXME: we need to make sure we are running in the correct environment
    path_to_pip = os.path.join(prefix, 'bin', 'pip')
    if not os.path.exists(path_to_pip):
        print("pip is not installed...")
        ret = 1
    else:
        try:
            ret = subprocess.call([path_to_pip,'install', s])
        except Exception as e:
            print("Error trying to run pip %s" % e)
            ret = 1
    if ret != 0:
        print("Could not install %s using pip" % s)
    return

def install_with_pip(prefix, index, specs):
    r = Resolve(index)
    for_conda = []

    try:
        r.find_matches(MatchSpec('pip')).next()
    except StopIteration:
        print("Pip not found, installing pip...")
        try:
            install_package(prefix, 'pip')
        except Exception as e:
            print("Could not install pip --- continuing...")
            return specs

    for s in specs:
        try:
            r.find_matches(MatchSpec(s)).next()
        except StopIteration:
            if s=='pip':
                for_conda.append(s)
                continue
            print("Conda package not available for %s, attempting to install via pip" % s)
            pip_install(prefix, s)
        else:
            for_conda.append(s)            
    return for_conda

