from install import available, linked
from resolve import Resolve


def name_dist(dist):
    return dist.rsplit('-', 2)[0]


def install_plan(prefix, index, specs):
    installed = linked(prefix)
    r = Resolve(index)

    must_have = {}
    for fn in r.solve(specs, ['%s.tar.bz2' % d for d in installed]):
        dist = fn[:-8]
        must_have[name_dist(dist)] = dist

    avail = available(join(sys.prefix, 'pkgs'))

    res = []
    for dist in must_have.itervalues():
        if dist not in avail:
            res.append(('FETCH', dist))
            res.append(('EXTRACT', dist))

    for dist in installed:
        name = name_dist(dist)
        if name in must_have and dist != must_have[name]:
            res.append(('UNLINK', dist))

    for dist in must_have.itervalues():
        if dist not in installed:
            res.append(('LINK', dist))

    return res


if __name__ == '__main__':
    import sys
    import json
    from pprint import pprint
    from os.path import dirname, join

    with open(join(dirname(__file__), '..', 'tests', 'index.json')) as fi:
        index = json.load(fi)

    res = install_plan(sys.prefix, index, ['w3lib'])
    pprint(res)
