from __future__ import absolute_import, division, print_function, unicode_literals

import errno
import json
import logging
import os
import re
import sys
import time
import warnings
from os.path import isdir, isfile, join

from .base.constants import DEFAULTS
from .core.linked_data import linked
from .exceptions import CondaFileIOError, CondaHistoryError
from .models.dist import Dist

log = logging.getLogger(__name__)


class CondaHistoryWarning(Warning):
    pass


def write_head(fo):
    fo.write("==> %s <==\n" % time.strftime('%Y-%m-%d %H:%M:%S'))
    fo.write("# cmd: %s\n" % (' '.join(sys.argv)))


def is_diff(content):
    return any(s.startswith(('-', '+')) for s in content)


def parse_content_line(s):
    if s.startswith(('-', '+')):
        pm = s[0]
        s = s[1:]
    else:
        pm = None
    parts = s.split()
    dist = Dist(parts[0])
    channel, dist_name = dist.pair
    if channel == DEFAULTS:
        channel = None
    if len(parts) == 1:
        dparts = dist_name.rsplit('-', 2)
        assert len(dparts) == 3
        name, version, build = dparts
        xtra = channel
    else:
        assert len(parts) == 4
        name, version, build = parts[1:]
        xtra = channel + '::' + dist_name if channel else dist_name
    name = name.lower()
    return pm, name, version, build, xtra


def pretty_diff(diff):
    added = {}
    removed = {}
    for parts in map(parse_content_line, diff):
        pm = parts[0]
        name = parts[1]
        if pm == '-':
            removed[name] = parts
        elif pm == '+':
            added[name] = parts
    changed = set(added) & set(removed)
    for name in sorted(changed):
        old = removed[name]
        new = added[name]
        if old[1:] == new[1:]:
            continue
        fmt0 = ' {1} '
        if old[2] != new[2]:
            fmt1 = '{2}'
        else:
            fmt1 = '{2}_{3}'
        fmt2 = fmt1 + ' ({4})' if new[4] else fmt1
        fmt1 = fmt1 + ' ({4})' if old[4] else fmt1
        yield '%s{%s -> %s}' % (fmt0.format(*old),
                                fmt1.format(*old), fmt2.format(*new))
    for pset in (removed, added):
        for name in sorted(set(pset) - changed):
            tmp = pset[name]
            fmt0 = '{0}{1} {2} {3}'
            fmt0 = fmt0 + ' {4}' if tmp[4] else fmt0
            yield fmt0.format(*tmp)


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
        self.update('enter')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.update('exit')

    def init_log_file(self, force=False):
        if not force and isfile(self.path):
            return
        self.write_dists(linked(self.prefix))

    def file_is_empty(self):
        return os.stat(self.path).st_size == 0

    def update(self, enter_or_exit=''):
        """
        update the history file (creating a new one if necessary)
        """
        try:
            self.init_log_file()
            try:
                last = set(self.get_state())
            except CondaHistoryError as e:
                warnings.warn("Error in %s: %s" % (self.path, e),
                              CondaHistoryWarning)
                return
            curr = set(map(str, linked(self.prefix)))
            if last == curr:
                # print a head when a blank env is first created to preserve history
                if enter_or_exit == 'exit' and self.file_is_empty():
                    with open(self.path, 'a') as fo:
                        write_head(fo)
                return
            self.write_changes(last, curr)
        except IOError as e:
            if e.errno == errno.EACCES:
                log.debug("Can't write the history file")
            else:
                raise CondaFileIOError(self.path, "Can't write the history file %s" % e)

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
                    item['specs'] = json.loads(specs.replace("'", '"'))
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
                        raise CondaHistoryError('Did not expect: %s' % s)
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
                    name, version, build, channel = Dist(pkg[1:]).quad
                    if pkg.startswith('+'):
                        added[name.lower()] = (version, build, channel)
                    elif pkg.startswith('-'):
                        removed[name.lower()] = (version, build, channel)

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
        if not isdir(self.meta_dir):
            os.makedirs(self.meta_dir)
        with open(self.path, 'w') as fo:
            if dists:
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
    # Don't use in context manager mode---it augments the history every time
    h = History(sys.prefix)
    pprint(h.get_user_requests())
