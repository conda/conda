# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

"""
Tools for converting conda packages

"""
from __future__ import print_function, division
import re
import tarfile

libpy_pat = re.compile(
    r'(lib/python\d\.\d|Lib)'
    r'/(site-packages|lib-dynload)/(\S+?)(\.cpython-\d\dm)?\.(so|pyd)')

def has_cext(t, show=False):
    matched = False
    for m in t.getmembers():
        match = libpy_pat.match(m.path)
        if match:
            if show:
                x = match.group(3)
                # XXX: Does this work for windows packages?
                print("import", x.replace('/', '.'))
                matched = True
            else:
                return True
    return matched

def tar_update(source, dest, file_map, verbose=True):
    """
    update a tarball, i.e. repack it and insert/update or remove some
    archives according file_map, which is a dictionary mapping archive names
    to either:

      - None:  meaning the archive will not be contained in the new tarball

      - a file path:  meaning the archive in the new tarball will be this
        file. Should point to an actual file on the filesystem.

      - a TarInfo object:  Useful when mapping from an existing archive. The
        file path in the archive will be the path in the TarInfo object. To
        change the path, mutate its .path attribute.

    Files in the source that aren't in the map will moved without any changes
    """

    # s -> t
    if isinstance(source, tarfile.TarFile):
        s = source
    else:
        if not source.endswith(('.tar', '.tar.bz2')):
            raise TypeError("path must be a .tar or .tar.bz2 path")
        s = tarfile.open(source)
    if isinstance(dest, tarfile.TarFile):
        t = dest
    else:
        t = tarfile.open(dest, 'w:bz2')

    try:
        for m in s.getmembers():
            p = m.path
            if p in file_map:
                if file_map[p] is None:
                    if verbose:
                        print('removing %r' % p)
                else:
                    if verbose:
                        print('updating %r with %r' % (p, file_map[p]))
                    if isinstance(file_map[p], tarfile.TarInfo):
                        t.addfile(file_map[p], s.extractfile(p))
                    else:
                        t.add(file_map[p], p)
                continue
            print("keeping %r" % p)
            t.addfile(m, s.extractfile(p))

        s_names_set = set(m.path for m in s.getmembers())
        for p in file_map:
            if p not in s_names_set:
                if verbose:
                    print('inserting %r with %r' % (p, file_map[p]))
                if isinstance(file_map[p], tarfile.TarInfo):
                    t.addfile(file_map[p], s.extractfile(p))
                else:
                    t.add(file_map[p], p)
    finally:
        t.close()
        s.close()
