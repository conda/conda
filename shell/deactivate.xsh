#!/usr/bin/env xonssh

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # DEACTIVATE FOR XONSH-SHELL                                          # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
import os
from argparse import ArgumentParser

from xonsh.tools import is_bool, to_bool


WHAT_SHELL_AM_I = "xonsh"

def _envvar_to_bool(name):
    if name in ${...}:
      var = ${name}
      rtn = var if is_bool(var) else to_bool(var)
    else:
      rtn = False
    return rtn


CONDA_HELP = _envvar_to_bool('CONDA_HELP')
CONDA_VERBOSE = _envvar_to_bool('CONDA_VERBOSE')


def _make_parser():
    p = ArgumentParser('activate.xsh', add_help=False)
    p.add_argument('-h', '--help', dest='help', default=CONDA_HELP,
                   action='store_true', help='show help')
    p.add_argument('-v', '--verbose', dest='verbose', default=CONDA_VERBOSE,
                   action='store_true', help='verbose mode')
    p.add_argument('unknown', nargs='?',
                   default='', help='unknown value')
    return p


def _parse_args(args=None):
    p = _make_parser()
    ns = p.parse_args(args=args)
    $CONDA_HELP = '1' if ns.help else '0'
    $CONDA_VERBOSE = '1' if ns.verbose else '0'
    if len(ns.unknown) > 0:
        ns.unknown = ' ' + ns.unknown
    return ns


def _cleanup():
    global os, ArgumentParser, is_bool, to_bool
    del os, ArgumentParser, is_bool, to_bool
    del $CONDA_HELP, $CONDA_VERBOSE


def _failsafe(pipeline=None):
    if not pipeline:
        _cleanup()
        raise RuntimeError("conda deactivate failed")


def _main(args=None):
    ns = _parse_args(args=args)
    if ns.help:
        _failsafe(![conda "..deactivate" @(WHAT_SHELL_AM_I) "-h" ""])
        _cleanup()
        return
    # CHECK IF CAN DEACTIVATE                                             #
    if 'CONDA_PREFIX' not in ${...} or len($CONDA_PREFIX) == 0:
        _cleanup()
        return
    # RESTORE PATH                                                        #
    # remove only first instance of $CONDA_PREFIX from $PATH, since this is#
    # Unix we will only expect a single path that need to be removed, for #
    # simplicity and consistency with the Windows *.bat scripts we will use#
    # fuzzy matching (/f) to get all of the relevant removals             #
    i = $PATH.index($CONDA_PREFIX)
    del $PATH[i]
    # REMOVE CONDA_PREFIX and CONDA_DEFAULT_ENV                           #
    conda_dir = os.path.join($CONDA_PREFIX, 'etc', 'conda', 'deactivate.d')
    del $CONDA_PREFIX, $CONDA_DEFAULT_ENV
    # LOAD POST-DEACTIVATE SCRIPTS                                        #
    if os.path.isdir(conda_dir):
        $cdslash = conda_dir + os.sep
        for fname in g`$cdslash*.sh`:
            f = os.path.join(conda_dir, fname)
            if ns.versbose:
                print("[DEACTIVATE]: Sourcing ${f}.".format(f=f))
            source-bash @(f)
        del cdslash
    _cleanup()


_main(args=$ARGS)
