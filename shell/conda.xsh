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

__all__ = ()


WHAT_SHELL_AM_I = "xonsh"

def _envvar_to_bool(name):
    if name in ${...}:
      var = ${name}
      rtn = var if is_bool(var) else to_bool(var)
    else:
      rtn = False
    return rtn

def _cleanup():
    del $CONDA_HELP, $CONDA_VERBOSE, $CONDA_ENVNAME


def _failsafe(pipeline=None, action='activate'):
    if not pipeline:
        _cleanup()
        raise RuntimeError("conda {} failed".format(action))

#
# activate
#

def _make_activate_parser():
    conda_help = _envvar_to_bool('CONDA_HELP')
    conda_verbose = _envvar_to_bool('CONDA_VERBOSE')
    conda_envname = $CONDA_ENVNAME if _envvar_to_bool('CONDA_ENVNAME') else 'root'
    p = ArgumentParser('activate', add_help=False)
    p.add_argument('-h', '--help', dest='help', default=conda_envname,
                   action='store_true', help='show help')
    p.add_argument('-v', '--verbose', dest='verbose', default=conda_verbose,
                   action='store_true', help='verbose mode')
    p.add_argument('envname', nargs='?',default=conda_envname,
                   help='environment name')
    return p


def _parse_activate_args(args=None):
    p = _make_activate_parser()
    ns = p.parse_args(args=args)
    $CONDA_HELP = '1' if ns.help else '0'
    $CONDA_VERBOSE = '1' if ns.verbose else '0'
    $CONDA_ENVNAME = ns.envname
    return ns


def __activate_main(args=None):
    ns = _parse_activate_args(args=args)
    if ns.help:
        _failsafe(![conda "..activate" @(WHAT_SHELL_AM_I) "-h" ""], 'activate')
        _cleanup()
        return
    # CHECK ENV AND DEACTIVATE OLD ENV
    _failsafe(![conda "..checkenv" @(WHAT_SHELL_AM_I) @(ns.envname)], 'activate')
    _deactivate_main(args=[""])
    pipeline = !(conda "..activate" @(WHAT_SHELL_AM_I) @(ns.envname))
    _failsafe(pipeline, 'activate')
    conda_bin = pipeline.out.strip()
    # update path with the new conda environment
    $PATH.insert(0, conda_bin)
    # CONDA_PREFIX
    # always the full path to the activated environment
    # is not set when no environment is active
    $CONDA_PREFIX = os.path.dirname(conda_bin)
    # CONDA_DEFAULT_ENV
    # the shortest representation of how conda recognizes your env
    # can be an env name, or a full path (if the string contains / it's a
    # path)
    if (os.sep in ns.envname) or (os.altsep is not None and
                                  os.altsep in ns.envname):
        $CONDA_DEFAULT_ENV = ns.envname
    else:
        d = os.path.abspath(os.path.dirname(ns.envname))
        f = os.path.basename(ns.envname)
        $CONDA_DEFAULT_ENV = os.path.join(d, f)
    # PS1 & CONDA_PS1_BACKUP
    # Prompt is set by xonsh itself. No need to later it here.
    # LOAD POST-ACTIVATE SCRIPTS
    # scripts found in $CONDA_PREFIX/etc/conda/activate.d
    conda_dir = os.path.join($CONDA_PREFIX, 'etc', 'conda', 'activate.d')
    if os.path.isdir(conda_dir):
        $cdslash = conda_dir + os.sep
        for fname in g`$cdslash*.xsh`:
            f = os.path.join(conda_dir, fname)
            if ns.versbose:
                print("[ACTIVATE]: Sourcing ${f}.".format(f=f))
            source @(f)
        del $cdslash
    _cleanup()


aliases['activate'] = _activate_main


#
# deactivate
#

def _make_deactivate_parser():
    conda_help = _envvar_to_bool('CONDA_HELP')
    conda_verbose = _envvar_to_bool('CONDA_VERBOSE')
    p = ArgumentParser('deactivate', add_help=False)
    p.add_argument('-h', '--help', dest='help', default=conda_help,
                   action='store_true', help='show help')
    p.add_argument('-v', '--verbose', dest='verbose', default=conda_verbose,
                   action='store_true', help='verbose mode')
    p.add_argument('unknown', nargs='?',
                   default='', help='unknown value')
    return p


def _parse_deactivate_args(args=None):
    p = _make_deactivate_parser()
    ns = p.parse_args(args=args)
    $CONDA_HELP = '1' if ns.help else '0'
    $CONDA_VERBOSE = '1' if ns.verbose else '0'
    $CONDA_ENVNAME = ''
    if len(ns.unknown) > 0:
        ns.unknown = ' ' + ns.unknown
    return ns


def _deactivate_main(args=None):
    ns = _parse_deactivate_args(args=args)
    if ns.help:
        _failsafe(![conda "..deactivate" @(WHAT_SHELL_AM_I) "-h" ""], 'deactivate')
        _cleanup()
        return
    # CHECK IF CAN DEACTIVATE
    if 'CONDA_PREFIX' not in ${...} or len($CONDA_PREFIX) == 0:
        _cleanup()
        return
    # RESTORE PATH
    # remove only first instance of $CONDA_PREFIX from $PATH, since this
    # is Unix we will only expect a single path that need to be removed
    # fuzzy matching (/f) removals will be used
    i = 0
    for p in $PATH:
        if p.startswith($CONDA_PREFIX):
            break
    else:
        i = None
    if i is not None:
        del $PATH[i]
    # REMOVE CONDA_PREFIX and CONDA_DEFAULT_ENV
    conda_dir = os.path.join($CONDA_PREFIX, 'etc', 'conda', 'deactivate.d')
    del $CONDA_PREFIX, $CONDA_DEFAULT_ENV
    # LOAD POST-DEACTIVATE SCRIPTS
    if os.path.isdir(conda_dir):
        $cdslash = conda_dir + os.sep
        for fname in g`$cdslash*.xsh`:
            f = os.path.join(conda_dir, fname)
            if ns.versbose:
                print("[DEACTIVATE]: Sourcing ${f}.".format(f=f))
            source @(f)
        del $cdslash
    _cleanup()


aliases['deactivate'] = _deactivate_main
