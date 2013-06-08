import os
import sys
import subprocess
from os.path import isdir, isfile, join

import config
import environ
import source
from scripts import BAT_PROXY

import conda.config as cc
import psutil


assert sys.platform == 'win32'


def fix_staged_scripts():
    """
    Fixes scripts which have been installed unix-style to have a .bat
    helper
    """
    scripts_dir = join(config.build_prefix, 'Scripts')
    if not isdir(scripts_dir):
        return
    for fn in os.listdir(scripts_dir):
        # process all the extensionless files
        if not isfile(join(scripts_dir, fn)) or '.' in fn:
            continue

        with open(join(scripts_dir, fn)) as f:
            line = f.readline().lower()
            # If it's a #!python script
            if not (line.startswith('#!') and 'python' in line.lower()):
                continue
            print('Adjusting unix-style #! script %s, '
                  'and adding a .bat file for it' % fn)
            # copy it with a .py extension (skipping that first #! line)
            with open(join(scripts_dir, fn + '-script.py'), 'w') as fo:
                fo.write(f.read())
            # now create the batch file
            with open(join(scripts_dir, fn + '.bat'), 'w') as fo:
                fo.write(BAT_PROXY)

        # remove the original script
        os.remove(join(scripts_dir, fn))


def msvc_env_cmd():
    vcvarsall = (r'C:\Program Files (x86)\Microsoft Visual Studio 9.0'
                 r'\VC\vcvarsall.bat')
    if not isfile(vcvarsall):
        raise RuntimeError("Couldn't find Visual Studio: %r" % vcvarsall)

    return 'call "%s" %s\n' % (vcvarsall,
                               {32: 'x86', 64: 'amd64'}[cc.bits])


def kill_processes():
    for n in psutil.get_pid_list():
        try:
            p = psutil.Process(n)
        except psutil._error.NoSuchProcess:
            continue
        if p.name.lower() == 'msbuild.exe':
            print 'Terminating:', p.name
            try:
                p.terminate()
            except psutil._error.NoSuchProcess:
                print '    no such process, passing'


def build(pkg):
    env = dict(os.environ)
    env.update(environ.get_dict(pkg))

    for name in 'BIN', 'INC', 'LIB':
        path = env['LIBRARY_' + name]
        if not isdir(path):
            os.makedirs(path)

    src_dir = source.get_dir()
    bld_bat = join(env['PKG_PATH'], 'bld.bat')
    with open(bld_bat) as fi:
        data = fi.read()
    with open(join(src_dir, 'bld.bat'), 'w') as fo:
        fo.write(msvc_env_cmd())
        # more debuggable with echo on
        fo.write('@echo on\n')
        for kv in env.iteritems():
            fo.write('set %s=%s\n' % kv)
        fo.write("REM ===== end generated header =====\n")
        fo.write(data)

    cmd = [os.environ['COMSPEC'], '/c', 'bld.bat']
    subprocess.check_call(cmd, cwd=src_dir)
    kill_processes()
    fix_staged_scripts()
