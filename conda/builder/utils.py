from os.path import normpath, getmtime, getsize

from conda.utils import md5_file



def rel_lib(f):
    assert not f.startswith('/')
    if f.startswith('lib/'):
        return normpath((f.count('/') - 1) * '../')
    else:
        return normpath(f.count('/') * '../') + '/lib'


def file_info(path):
    return {'size': getsize(path),
            'md5': md5_file(path),
            'mtime': getmtime(path)}
