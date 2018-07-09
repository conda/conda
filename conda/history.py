from __future__ import absolute_import, division, print_function, unicode_literals

from ast import literal_eval
from errno import EACCES, EPERM
import logging
from operator import itemgetter
import os
from os.path import isdir, isfile, join
import re
import sys
from textwrap import dedent
import time
import warnings

from . import __version__ as CONDA_VERSION
from ._vendor.auxlib.ish import dals
from .base.constants import DEFAULTS_CHANNEL_NAME
from .common.compat import ensure_text_type, open
from .core.linked_data import linked
from .models.dist import Dist
from .base.context import context
from .common.path import paths_equal
from .version import VersionOrder, version_relation_re
from .exceptions import CondaHistoryError, CondaUpgradeError, NotWritableError

try:
    from cytoolz.itertoolz import groupby, take
except ImportError:  # pragma: no cover
    from ._vendor.toolz.itertoolz import groupby, take  # NOQA


log = logging.getLogger(__name__)


class CondaHistoryWarning(Warning):
    pass


def write_head(fo):
    fo.write("==> %s <==\n" % time.strftime('%Y-%m-%d %H:%M:%S'))
    fo.write("# cmd: %s\n" % (' '.join(ensure_text_type(s) for s in sys.argv)))
    fo.write("# conda version: %s\n" % '.'.join(take(3, CONDA_VERSION.split('.'))))


def is_diff(content):
    return any(s.startswith(('-', '+')) for s in content)


def pretty_diff(diff):
    added = {}
    removed = {}
    for s in diff:
        fn = s[1:]
        dist = Dist(fn)
        name, version, _, channel = dist.quad
        if channel != DEFAULTS_CHANNEL_NAME:
            version += ' (%s)' % channel
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

    com_pat = re.compile(r'#\s*cmd:\s*(.+)')
    spec_pat = re.compile(r'#\s*(\w+)\s*specs:\s*(.+)?')
    conda_v_pat = re.compile(r'#\s*conda version:\s*(.+)')

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
        except EnvironmentError as e:
            if e.errno in (EACCES, EPERM):
                raise NotWritableError(self.path, e.errno)
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

    @staticmethod
    def _parse_old_format_specs_string(specs_string):
        """
        Parse specifications string that use conda<4.5 syntax.

        Examples
        --------
          - "param >=1.5.1,<2.0'"
          - "python>=3.5.1,jupyter >=1.0.0,<2.0,matplotlib >=1.5.1,<2.0"
        """
        specs = []
        for spec in specs_string.split(','):
            # If the spec starts with a version qualifier, then it actually belongs to the
            # previous spec. But don't try to join if there was no previous spec.
            if version_relation_re.match(spec) and specs:
                specs[-1] = ','.join([specs[-1], spec])
            else:
                specs.append(spec)
        return specs

    @classmethod
    def _parse_comment_line(cls, line):
        """
        Parse comment lines in the history file.

        These lines can be of command type or action type.

        """
        item = {}
        m = cls.com_pat.match(line)
        if m:
            argv = m.group(1).split()
            if argv[0].endswith('conda'):
                argv[0] = 'conda'
            item['cmd'] = argv

        m = cls.conda_v_pat.match(line)
        if m:
            item['conda_version'] = m.group(1)

        m = cls.spec_pat.match(line)
        if m:
            action, specs_string = m.groups()
            specs_string = specs_string or ""
            item['action'] = action

            if specs_string.startswith('['):
                specs = literal_eval(specs_string)
            elif '[' not in specs_string:
                specs = History._parse_old_format_specs_string(specs_string)

            specs = [spec for spec in specs if spec and not spec.endswith('@')]

            if specs and action in ('update', 'install', 'create'):
                item['update_specs'] = item['specs'] = specs
            elif specs and action in ('remove', 'uninstall'):
                item['remove_specs'] = item['specs'] = specs

        return item

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
        for dt, unused_cont, comments in self.parse():
            item = {'date': dt}
            for line in comments:
                comment_items = self._parse_comment_line(line)
                item.update(comment_items)

            if 'cmd' in item:
                res.append(item)

            dists = groupby(itemgetter(0), unused_cont)
            item['unlink_dists'] = dists.get('-', ())
            item['link_dists'] = dists.get('+', ())

        conda_versions_from_history = tuple(x['conda_version'] for x in res
                                            if 'conda_version' in x)
        if conda_versions_from_history:
            minimum_conda_version = sorted(conda_versions_from_history, key=VersionOrder)[-1]
            minimum_major_minor = '.'.join(take(2, minimum_conda_version.split('.')))
            current_major_minor = '.'.join(take(2, CONDA_VERSION.split('.')))
            if VersionOrder(current_major_minor) < VersionOrder(minimum_major_minor):
                message = dals("""
                This environment has previously been operated on by a conda version that's newer
                than the conda currently being used. A newer version of conda is required.
                  target environment location: %(target_prefix)s
                  current conda version: %(conda_version)s
                  minimum conda version: %(minimum_version)s
                """) % {
                    "target_prefix": self.prefix,
                    "conda_version": CONDA_VERSION,
                    "minimum_version": minimum_major_minor,
                }
                if not paths_equal(self.prefix, context.root_prefix):
                    message += dedent("""
                    Update conda and try again.
                        $ conda install -p "%(base_prefix)s" "conda>=%(minimum_version)s"
                    """) % {
                        "base_prefix": context.root_prefix,
                        "minimum_version": minimum_major_minor,
                    }
                raise CondaUpgradeError(message)

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
