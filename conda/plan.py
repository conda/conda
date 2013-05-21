from install import available, linked
from resolve import Resolve


def split_dist(dist):
    n, v, b = dist.rsplit('-', 2)
    return n, v + b


def install_plan(prefix, index, specs):
    installed = linked(prefix)
    r = Resolve(index)

    must_have = {}
    for fn in r.solve(specs, ['%s.tar.bz2' % d for d in installed]):
        dist = fn[:-8]
        n, vb = split_dist(dist)
        must_have[n] = dist

    avail = available(join(sys.prefix, 'pkgs'))

    res = []
    for dist in must_have.itervalues():
        if dist not in avail:
            res.append(('FETCH', dist))
            res.append(('EXTRACT', dist))

    for dist in installed:
        n, vb = split_dist(dist)
        if n in must_have and dist != must_have[n]:
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
