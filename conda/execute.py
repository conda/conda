import sys
from collections import defaultdict
from os.path import join

import install
from naming import name_dist
from remote import fetch_file
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar


PKGS_DIR = join(sys.prefix, 'pkgs')


def parse(plan):
    actions = defaultdict(list)
    prefix = None
    for a0, a1 in plan:
        if a0 == '#':
            continue
        elif a0 == 'PREFIX':
            prefix = a1
        elif a0 in ('FETCH', 'EXTRACT', 'REMOVE', 'UNLINK', 'LINK'):
            actions[a0].append(a1)
        else:
            raise
    return prefix, actions

def display(plan):
    from pprint import pprint
    pprint(parse(plan))

def fetch(index, dists, progress):
    if progress and dists:
        print "Fetching packages..."
    for dist in dists:
        fn = dist + '.tar.bz2'
        info = index[fn]
        fetch_file(info['channel'], fn, md5=info['md5'], size=info['size'],
                   progress=progress)

def extract(dist, unused_prefix):
    "Extracting packages ..."
    install.make_available(PKGS_DIR, dist)

def remove(dist, unused_prefix):
    "Removing packages ..."
    install.remove_available(PKGS_DIR, dist)

def link(dist, prefix):
    "Linking packages ..."
    install.link(PKGS_DIR, dist, prefix)

def unlink(dist, prefix):
    "Unlinking packages ..."
    install.unlink(dist, prefix)

def handle(prefix, dists, cb_func, progress):
    if not dists:
        return
    if progress:
        print cb_func.__doc__.strip()
        progress.maxval = len(dists)
        progress.start()
    for i, dist in enumerate(dists):
        if progress:
            progress.widgets[0] = '[%-20s]' % name_dist(dist)
            progress.update(i + 1)
        cb_func(dist, prefix)
    if progress:
        progress.widgets[0] = '[      COMPLETE      ]'
        progress.finish()

def execute(plan, index=None, progress_bar=True):
    if progress_bar:
        fetch_progress = ProgressBar(
            widgets=['', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
                     FileTransferSpeed()])
        progress = ProgressBar(
            widgets=['', ' ', Bar(), ' ', Percentage()])
    else:
        fetch_progress = None
        progress = None

    prefix, actions = parse(plan)
    fetch(index or {}, actions['FETCH'], fetch_progress)
    handle(None, actions['EXTRACT'], extract, progress)
    handle(None, actions['REMOVE'], remove, progress)
    handle(prefix, actions['LINK'], link, progress)
    handle(prefix, actions['UNLINK'], unlink, progress)


if __name__ == '__main__':
    #from plan import _test_plan
    #display(_test_plan())
    from api import get_index

    plan = [
        ('#', 'install_plan'),
        ('PREFIX', '/home/ilan/a150/envs/test'),
        #('FETCH',   'mkl-rt-11.0-p0'),
        ('EXTRACT', 'python-2.7.5-0'),
        ('EXTRACT', 'scipy-0.11.0-np17py26_p3'),
        ('EXTRACT', 'mkl-rt-11.0-p0'),
        ('LINK',    'python-2.7.5-0'),
        ('UNLINK',  'python-2.7.5-0'),
    ]
    execute(plan, get_index())
