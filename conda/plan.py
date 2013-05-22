import sys
from collections import defaultdict
from os.path import join

import install
from naming import name_dist
from resolve import Resolve


PKGS_DIR = join(sys.prefix, 'pkgs')


def install_plan(prefix, index, specs):
    linked = install.linked(prefix)
    extracted = install.extracted(PKGS_DIR)
    fetched = install.fetched(PKGS_DIR)

    r = Resolve(index)

    must_have = {}
    for fn in r.solve(specs, ['%s.tar.bz2' % d for d in linked]):
        dist = fn[:-8]
        must_have[name_dist(dist)] = dist
    sorted_must_have = sorted(must_have.values())

    actions = defaultdict(list)
    for dist in sorted_must_have:
        if dist in linked:
            continue
        actions['LINK'].append(dist)
        if dist in extracted:
            continue
        actions['EXTRACT'].append(dist)
        if dist in fetched:
            continue
        actions['FETCH'].append(dist)

    for dist in sorted(linked):
        name = name_dist(dist)
        if name in must_have and dist != must_have[name]:
            actions['UNLINK'].append(dist)

    res = ['# install_plan',
           'PREFIX %s' % prefix]
    for op in 'FETCH', 'EXTRACT', 'UNLINK', 'LINK':
        if not actions[op]:
            continue
        res.append('PRINT %sing packages ...' % op.capitalize())
        if op != 'FETCH':
            res.append('START %d' % len(actions[op]))
        for dist in actions[op]:
            res.append('%s %s' % (op, dist))
    return res


def _test_plan():
    import sys
    import json

    with open(join('..', 'tests', 'index.json')) as fi:
        index = json.load(fi)
    return install_plan(sys.prefix, index, ['w3lib'])

if __name__ == '__main__':
    from pprint import pprint
    pprint(_test_plan())
