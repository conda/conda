

def name_dist(dist):
    return dist.rsplit('-', 2)[0]


def fn2spec(fn):
    assert fn.endswith('.tar.bz2')
    return ' '.join(fn[:-8].rsplit('-', 2))
