from os.path import join

from conda.cli.common import name_prefix, error_and_exit
from conda.config import envs_dirs, root_dir


def read_message(fn):
    res = []
    for envs_dir in envs_dirs:
        path = join(envs_dir, '.conda-help', fn)
        try:
            with open(path) as fi:
                s = fi.read().decode('utf-8')
            s = s.replace('${envs_dir}', envs_dir)
            res.append(s)
        except IOError:
            pass
    return ''.join(res)


def root_read_only(command, prefix, json=False):
    assert command in {'install', 'update', 'remove'}

    msg = read_message('ro.txt')
    if not msg:
        msg = """\
Missing write permissions in: ${root_dir}
#
# You don't appear to have the necessary permissions to ${command} packages
# into the install area '${root_dir}'.
# However you can clone this environment into your home directory and
# then make changes to it.
# This may be done using the command:
#
# $ conda create -n my_${name} --clone=${prefix}
"""
    msg = msg.replace('${root_dir}', root_dir)
    msg = msg.replace('${prefix}', prefix)
    msg = msg.replace('${name}', name_prefix(prefix))
    msg = msg.replace('${command}', command)
    error_and_exit(msg, json=json, error_type='RootNotWritable')
