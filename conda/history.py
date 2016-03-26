from __future__ import print_function, division, absolute_import

import os
import re
import sys
import time
from os.path import isdir, isfile, join
import warnings
import errno
import logging

from conda import install

log = logging.getLogger(__name__)

class CondaHistoryException(Exception):
    pass


class CondaHistoryWarning(Warning):
    pass


def write_head(fo):
    fo.write("==> %s <==\n" % time.strftime('%Y-%m-%d %H:%M:%S'))
    fo.write("# cmd: %s\n" % (' '.join(sys.argv)))


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
        self.meta_dir = join(prefix, 'conda-meta')
        self.path = join(self.meta_dir, 'history')

    def __enter__(self):
        self.update()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.update()

    def init_log_file(self, force=False):
        if not force and isfile(self.path):
            return
        self.write_dists(install.linked(self.prefix))

    def update(self):
        """
        update the history file (creating a new one if necessary)
        """
        try:
            self.init_log_file()
            try:
                last = self.get_state()
            except CondaHistoryException as e:
                warnings.warn("Error in %s: %s" % (self.path, e),
                              CondaHistoryWarning)
                return
            curr = set(install.linked(self.prefix))
            if last == curr:
                return
            self.write_changes(last, curr)
        except IOError as e:
            if e.errno == errno.EACCES:
                log.debug("Can't write the history file")
            else:
                raise

    def parse(self):
        """
        parse the history file and return a list of
        tuples(datetime strings, set of distributions/diffs, comments)
        """
        res = []
        if not isfile(self.path):
            return res
        sep_pat = re.compile(r'==>\s*(.+?)\s*<==')
        with open(self.path) as f:
            lines = f.read().splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            m = sep_pat.match(line)
            if m:
                res.append((m.group(1), set(), []))
            elif line.startswith('#'):
                res[-1][2].append(line)
            else:
                res[-1][1].add(line)
        return res

    def get_user_requests(self):
        """
        return a list of user requested items.  Each item is a dict with the
        following keys:
        'date': the date and time running the command
        'cmd': a list of argv of the actual command which was run
        'action': install/remove/update
        'specs': the specs being used
        """
        res = []
        com_pat = re.compile(r'#\s*cmd:\s*(.+)')
        spec_pat = re.compile(r'#\s*(\w+)\s*specs:\s*(.+)')
        for dt, unused_cont, comments in self.parse():
            item = {'date': dt}
            for line in comments:
                m = com_pat.match(line)
                if m:
                    argv = m.group(1).split()
                    if argv[0].endswith('conda'):
                        argv[0] = 'conda'
                    item['cmd'] = argv
                m = spec_pat.match(line)
                if m:
                    action, specs = m.groups()
                    item['action'] = action
                    item['specs'] = eval(specs)
            if 'cmd' in item:
                res.append(item)
        return res

    def construct_states(self):
        """
        return a list of tuples(datetime strings, set of distributions)
        """
        res = []
        cur = set([])
        for dt, cont, unused_com in self.parse():
            if not is_diff(cont):
                cur = cont
            else:
                for s in cont:
                    if s.startswith('-'):
                        cur.discard(s[1:])
                    elif s.startswith('+'):
                        cur.add(s[1:])
                    else:
                        raise CondaHistoryException('Did not expect: %s' % s)
            res.append((dt, cur.copy()))
        return res

    def get_state(self, rev=-1):
        """
        return the state, i.e. the set of distributions, for a given revision,
        defaults to latest (which is the same as the current state when
        the log file is up-to-date)
        """
        states = self.construct_states()
        if not states:
            return set([])
        times, pkgs = zip(*states)
        return pkgs[rev]

    def print_log(self):
        for i, (date, content, unused_com) in enumerate(self.parse()):
            print('%s  (rev %d)' % (date, i))
            for line in pretty_content(content):
                print('    %s' % line)
            print()

    def object_log(self):
        result = []
        for i, (date, content, unused_com) in enumerate(self.parse()):
            # Based on Mateusz's code; provides more details about the
            # history event
            event = {
                'date': date,
                'rev': i,
                'install': [],
                'remove': [],
                'upgrade': [],
                'downgrade': []
            }
            added = {}
            removed = {}
            if is_diff(content):
                for pkg in content:
                    name, version, build = pkg[1:].rsplit('-', 2)
                    if pkg.startswith('+'):
                        added[name.lower()] = (version, build)
                    elif pkg.startswith('-'):
                        removed[name.lower()] = (version, build)

                changed = set(added) & set(removed)
                for name in sorted(changed):
                    old = removed[name]
                    new = added[name]
                    details = {
                        'old': '-'.join((name,) + old),
                        'new': '-'.join((name,) + new)
                    }

                    if new > old:
                        event['upgrade'].append(details)
                    else:
                        event['downgrade'].append(details)

                for name in sorted(set(removed) - changed):
                    event['remove'].append('-'.join((name,) + removed[name]))

                for name in sorted(set(added) - changed):
                    event['install'].append('-'.join((name,) + added[name]))
            else:
                for pkg in sorted(content):
                    event['install'].append(pkg)
            result.append(event)
        return result

    def write_dists(self, dists):
        if not dists:
            return
        if not isdir(self.meta_dir):
            os.makedirs(self.meta_dir)
        with open(self.path, 'w') as fo:
            write_head(fo)
            for dist in sorted(dists):
                fo.write('%s\n' % dist)

    def write_changes(self, last_state, current_state):
        with open(self.path, 'a') as fo:
            write_head(fo)
            for fn in sorted(last_state - current_state):
                fo.write('-%s\n' % fn)
            for fn in sorted(current_state - last_state):
                fo.write('+%s\n' % fn)

if __name__ == '__main__':
    from pprint import pprint
    with History(sys.prefix) as h:
        pprint(h.get_user_requests())
