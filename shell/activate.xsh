#!/usr/bin/env xonsh

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # ACTIVATE FOR XONSH-SHELL                                            # #
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
CONDA_ENVNAME = $CONDA_ENVNAME if _envvar_to_bool('CONDA_ENVNAME') else 'root'


def _make_parser():
    p = ArgumentParser('activate.xsh', add_help=False)
    p.add_argument('-h', '--help', dest='help', default=CONDA_HELP,
                   action='store_true', help='show help')
    p.add_argument('-v', '--verbose', dest='verbose', default=CONDA_VERBOSE,
                   action='store_true', help='verbose mode')
    p.add_argument('envname', nargs='?', dest='envname',
                   default=CONDA_ENVNAME, help='environment name')
    return p


def _parse_args(args=None):
    p = _make_parser()
    ns = p.parse_args(args=args)
    $CONDA_HELP = '1' if ns.help else '0'
    $CONDA_VERBOSE = '1' if ns.verbose else '0'
    $CONDA_ENVNAME = ns.envname
    return ns


def _cleanup():
    global os, ArgumentParser, is_bool_to_bool
    del os, ArgumentParser, is_bool_to_bool
    del $CONDA_HELP, $CONDA_VERBOSE, $CONDA_ENVNAME


def _failsafe(pipeline=None):
    if not pipeline:
        _cleanup()
        raise RuntimeError("conda activate failed")


def _main(args=None):
    ns = _parse_args(args=args)
    if ns.help:
        _failsafe(![conda "..activate" @(WHAT_SHELL_AM_I) "-h" ""])
        _cleanup()
        return
    # CHECK ENV AND DEACTIVATE OLD ENV                                    #
    _failsafe(![conda "..checkenv" @(WHAT_SHELL_AM_I) @(ns.envname)])
    _failsafe(![source deactivate.xsh ""])
    pipeline = !(conda "..activate" @(WHAT_SHELL_AM_I) @(ns.envname))
    _failsafe(pipeline)
    conda_bin = pipeline.out.strip()
    # update path with the new conda environment                          #
    $PATH.insert(0, conda_bin)
    # CONDA_PREFIX                                                        #
    # always the full path to the activated environment                   #
    # is not set when no environment is active                            #
    $CONDA_PREFIX = os.path.dirname(conda_bin)
    # CONDA_DEFAULT_ENV                                                   #
    # the shortest representation of how conda recognizes your env        #
    # can be an env name, or a full path (if the string contains / it's a #
    # path)                                                               #
    if os.sep in ns.envname or os.altsep in ns.envname:
        $CONDA_DEFAULT_ENV = ns.envname
    else:
        d = os.path.abspath(os.path.dirname(ns.envname))
        f = os.path.basename(ns.envname)
        $CONDA_DEFAULT_ENV = os.path.join(d, f)
    # PS1 & CONDA_PS1_BACKUP                                              #
    # Prompt is set by xonsh itself. No need to later it here.            #
    # LOAD POST-ACTIVATE SCRIPTS                                          #
    # scripts found in $CONDA_PREFIX/etc/conda/activate.d                 #
    conda_dir = os.path.join($CONDA_PREFIX, 'etc', 'conda', 'activate.d')
    if os.path.isdir(conda_dir):
        $cdslash = conda_dir + os.sep
        for fname in g`$cdslash*.sh`:
            f = os.path.join(conda_dir, fname)
            if ns.versbose:
                print("[ACTIVATE]: Sourcing ${f}.".format(f=f))
            source-bash @(f)
        del cdslash
    _cleanup()


_main(args=$ARGS)
