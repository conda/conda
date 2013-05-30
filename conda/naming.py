

def name_dist(dist):
    assert not dist.endswith('.tar.bz2')
    return dist.rsplit('-', 2)[0]


def name_fn(fn):
    assert fn.endswith('.tar.bz2')
    return name_dist(fn[:-8])


def fn2spec(fn):
    assert fn.endswith('.tar.bz2')
    return ' '.join(fn[:-8].rsplit('-', 2))
