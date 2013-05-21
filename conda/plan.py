import sys
from os.path import join

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
    sorted_must_have = sorted(must_have.values())

    res = [('#', 'install_plan'),
           ('PREFIX', prefix)]
    # TODO: split install.available into downloaded and extracted
    avail = available(join(sys.prefix, 'pkgs'))
    for dist in sorted_must_have:
        if dist not in avail:
            res.append(('FETCH', dist))

    for dist in sorted_must_have:
        if dist not in avail:
            res.append(('EXTRACT', dist))

    for dist in sorted(installed):
        name = name_dist(dist)
        if name in must_have and dist != must_have[name]:
            res.append(('UNLINK', dist))

    for dist in sorted_must_have:
        if dist not in installed:
            res.append(('LINK', dist))

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
