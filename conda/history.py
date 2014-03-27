from __future__ import print_function, division, absolute_import

import re
import sys
import time
from os.path import isfile, join

from conda import install


TIME_FORMAT = '%Y-%m-%d %H:%M:%S %z %Z'


def now():
    """
    return the current local time as an ISO formated
    string with time zone data, e.g. '2014-03-26 18:12:45 -0500 CDT'
    """
    return time.strftime(TIME_FORMAT)


def is_diff(content):
    return any(s.startswith(('-', '+')) for s in content)


def pretty_diff(diff):
    added = {}
    removed = {}
    for s in diff:
        fn = s[1:]
        name, version, unused_build = fn.rsplit('-', 2)
        if s.startswith('-'):
            removed[name.lower()] = version
        elif s.startswith('+'):
            added[name.lower()] = version
    changed = set(added) & set(removed)
    for name in sorted(changed):
        yield ' %s  {%s -> %s}' % (name, removed[name], added[name])
    for name in sorted(set(removed) - changed):
        yield '-%s-%s' % (name, removed[name])
    for name in sorted(set(added) - changed):
        yield '+%s-%s' % (name, added[name])


def pretty_content(content):
    if is_diff(content):
        return pretty_diff(content)
    else:
        return iter(sorted(content))


class History(object):

    def __init__(self, prefix):
        self.prefix = prefix
        if prefix is None:
            return
        self.path = join(prefix, 'conda-meta/history')

    def __enter__(self):
        if self.prefix is None:
            return
        self.update()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.prefix is None:
            return
        self.update()

    def init_log_file(self, force=False):
        if not force and isfile(self.path):
            return
        self.write_dists(install.linked(self.prefix))

    def update(self):
        """
        update the history file (creating a new one if necessary)
        """
        self.init_log_file()
        last = self.get_state()
        curr = set(install.linked(self.prefix))
        if last == curr:
            return
        self.write_changes(last, curr)

    def parse(self):
        """
        parse the history file and return a list of
        tuples(datetime strings, set of distributions/diffs)
        """
        res = []
        if not isfile(self.path):
            return res
        sep_pat = re.compile(r'==>\s*(.+?)\s*<==')
        for line in open(self.path):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = sep_pat.match(line)
            if m:
                dt = m.group(1)
                res.append((dt, set()))
            else:
                res[-1][1].add(line)
        return res

    def construct_states(self):
        """
        return a list of tuples(datetime strings, set of distributions)
        """
        res = []
        for dt, cont in self.parse():
            if not is_diff(cont):
                cur = cont
            else:
                for s in cont:
                    if s.startswith('-'):
                        cur.discard(s[1:])
                    elif s.startswith('+'):
                        cur.add(s[1:])
                    else:
                        raise Exception('Did not expect: %s' % s)
            res.append((dt, cur.copy()))
        return res

    def get_state(self, rev=-1):
        """
        return the state, i.e. the set of distributions, for a given revision,
        defaults to latest (which is the same as the current state when
        the log file is up-to-date)
        """
        times, pkgs = zip(*self.construct_states())
        return pkgs[rev]

    def print_log(self):
        for i, (date, content) in enumerate(self.parse()):
            print('%s  (rev %d)' % (date, i))
            for line in pretty_content(content):
                print('    %s' % line)
            print()

    def write_dists(self, dists):
        fo = open(self.path, 'w')
        fo.write("==> %s <==\n" % now())
        for dist in dists:
            fo.write('%s\n' % dist)
        fo.close()

    def write_changes(self, last_state, current_state):
        fo = open(self.path, 'a')
        fo.write("==> %s <==\n" % now())
        for fn in last_state - current_state:
            fo.write('-%s\n' % fn)
        for fn in current_state - last_state:
            fo.write('+%s\n' % fn)
        fo.close()


if __name__ == '__main__':
    h = History(sys.prefix)
    with h:
        h.update()
        h.print_log()
