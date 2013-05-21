import sys
from collections import defaultdict
from os.path import join

import install
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
        elif a0 in ('FETCH', 'EXTRACT', 'UNLINK', 'LINK'):
            actions[a0].append(a1)
        else:
            raise
    if prefix is None:
        raise
    return prefix, dict(actions)

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
    install.make_available(PKGS_DIR, dist)

def link(dist, prefix):
    install.link(PKGS_DIR, dist, prefix)

def unlink(dist, prefix):
    install.unlink(dist, prefix)

def handle_packages(prefix, dists, cb_func, progress):
    if not dists:
        return
    if progress:
        print "Extracting packages..."
        progress.maxval = len(dists)
        progress.start()
    for i, dist in enumerate(dists):
        if progress:
            progress.widgets[0] = '[%-20s]' % dist
            progress.update(i)
        cb_func(dist, prefix)
    if progress:
        progress.widgets[0] = '[      COMPLETE      ]'
        progress.finish()

def execute(plan, index, progress_bar=True):
    if progress_bar:
        download_progress = ProgressBar(
            widgets=['', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
                     FileTransferSpeed()])
        package_progress = ProgressBar(
            widgets=['', ' ', Bar(), ' ', Percentage()])
    else:
        download_progress = None
        package_progress = None

    prefix, actions = parse(plan)
    fetch(index, actions['FETCH'], download_progress)
    handle_packages(prefix, actions['EXTRACT'], extract, package_progress)
    handle_packages(prefix, actions['LINK'], link, package_progress)
    handle_packages(prefix, actions['UNLINK'], unlink, package_progress)


if __name__ == '__main__':
    from plan import _test_plan
    display(_test_plan())
