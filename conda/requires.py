"""
This module is for backwards compatibility with the Launcher. All
functions contained are deprecated and should not be usd for any
new development.
"""
import os
import sys
from os.path import exists, join


PKGS_DIR = join(sys.prefix, 'pkgs')

def read_requires(pkg):
    res = []
    path = join(PKGS_DIR, pkg, 'info/requires')
    if not exists(path):
        return res
    for line in open(path):
        r = line.strip()
        if r.endswith(('pro0', 'ce0')):
            if r.endswith('pro0'):
                x = r[:-4]
            else:
                x = r[:-3]
            r = x + ('ce0' if 'AnacondaCE' in sys.version else 'pro0')
        if r.startswith('mkl-') or not r:
            continue
        res.append(r)
    return res


def get_all_deps():
    res = {}
    for fn in os.listdir(PKGS_DIR):
        res[fn] = read_requires(fn)
    return res


def get_deps(pkgs):
    all_deps = get_all_deps()
    if isinstance(pkgs, str):
        return all_deps[pkgs]
    deps = set([])
    for pkg in pkgs:
        deps = deps.union(set(all_deps[pkg]))
    return sorted(list(deps))


def get_all_reverse_deps():
    res = {}
    deps = get_all_deps()
    for k,v in deps.items():
        for p in v:
            if p not in res:
                res[p] = []
            res[p].append(k)
    return res


def get_reverse_deps(pkgs):
    all_rdeps = get_all_reverse_deps()
    if isinstance(pkgs, str):
        return all_rdeps[pkgs]
    rdeps = set([])
    for pkg in pkgs:
        rdeps = rdeps.union(set(all_rdeps[pkg]))
    return sorted(list(rdeps))
