"""
this module is directly invoked by the (self extracting (sfx)) tarball
installer to create the initial environment, therefore it needs to be
standalone, i.e. not import any other parts of conda (only depend of
the standard library).
"""
import os
import stat
import sys
import logging
from os.path import isdir, join


log = logging.getLogger(__name__)


def yield_lines(path):
    for line in open(path):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        yield line


def change_prefix(path, new_prefix):
    with open(path) as fi:
        data = fi.read()
    new_data = data.replace('/opt/anaconda1anaconda2'
                            # the build prefix is intentionally split into
                            # parts, such that running this program on itself
                            # will leave it unchanged
                            'anaconda3', new_prefix)
    if new_data == data:
        return
    st = os.stat(path)
    os.unlink(path)
    with open(path, 'w') as fo:
        fo.write(new_data)
    os.chmod(path, stat.S_IMODE(st.st_mode))


def sfx_activate(pkgs_dir, dist, prefix):
    dist_path = join(pkgs_dir, dist)
    for f in yield_lines(join(dist_path, 'info/files')):
        src = join(dist_path, f)
        fdn, fbn = os.path.split(f)
        dst_dir = join(prefix, fdn)
        if not isdir(dst_dir):
            os.makedirs(dst_dir)
        dst = join(dst_dir, fbn)
        if os.path.exists(dst):
            log.warn("file already exists: '%s'" % dst)
        else:
            try:
                os.link(src, dst)
            except OSError:
                log.error('failed to link (src=%r, dst=%r)' % (src, dst))

    for f in yield_lines(join(dist_path, 'info/has_prefix')):
        change_prefix(join(prefix, f), prefix)


if __name__ == '__main__':
    prefix = sys.argv[1]
    pkgs_dir = join(prefix, 'pkgs')

    for dist in sorted(os.listdir(pkgs_dir)):
        sfx_activate(pkgs_dir, dist, prefix)
