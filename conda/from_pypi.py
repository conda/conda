from __future__ import print_function, division, absolute_import
from conda.resolve import MatchSpec, Resolve
import argparse
import os.path
from conda.cli import main_skeleton
from conda.cli import main_build
from conda.cli import main_install
from conda.builder import build, config, metadata

def configure_and_call_function(args, message):
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
        print("Unable to %s for %s" % (message, e))


def create_recipe(prefix, spec):
    rootdir = config.root_dir
    direc = os.path.join(rootdir, 'conda-recipes', spec)
    args = ['skeleton','pypi', spec, '--no-prompt','--output-dir', direc]
    configure_and_call_function(args, "create recipe")
    # conda skeleton pypi spec --no-prompt --output-dir root/conda-recipes/spec
    return direc

def build_pacakge(prefix, recipedir):
    args = ['build', recipedir, '--no-binstar-upload']
    configure_and_call_function(args, "build recipe")
    pkgname = build.bldpkg_path(metadata.MetaData(recipedir))
    # conda build recipedir --no-binstar-upload
    return pkgname

def install_package(prefix, pkgname):
    args = ['install', pkgname]
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
            recipedir = create_recipe(prefix, s)
            pkgname = build_package(prefix, recipedir)
            install_package(prefix, pkgname)
        else:
            for_conda.append(s)            
    return for_conda
