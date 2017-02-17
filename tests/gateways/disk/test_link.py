# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger
import os
from os.path import join, isdir, lexists, isfile, exists
from tempfile import gettempdir
from unittest import TestCase
import uuid

from conda.common.compat import on_win, PY2

from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.link import link, islink, readlink, stat_nlink, symlink
from conda.gateways.disk.update import touch

log = getLogger(__name__)


class LinkSymlinkUnlinkIslinkReadlinkTests(TestCase):

    def setUp(self):
        tempdirdir = gettempdir()
        dirname = str(uuid.uuid4())[:8]
        self.test_dir = join(tempdirdir, dirname)
        mkdir_p(self.test_dir)
        assert isdir(self.test_dir)

    def tearDown(self):
        rm_rf(self.test_dir)
        assert not lexists(self.test_dir)

    def test_hard_link(self):
        path1_real_file = join(self.test_dir, 'path1_real_file')
        path2_second_inode = join(self.test_dir, 'path2_second_inode')
        touch(path1_real_file)
        assert isfile(path1_real_file)
        assert not islink(path1_real_file)
        link(path1_real_file, path2_second_inode)
        assert isfile(path2_second_inode)
        assert not islink(path2_second_inode)

        path1_stat = os.stat(path1_real_file)
        path2_stat = os.stat(path2_second_inode)

        assert path1_stat.st_ino == path2_stat.st_ino
        assert stat_nlink(path1_real_file) == stat_nlink(path2_second_inode)

        os.unlink(path2_second_inode)
        assert not lexists(path2_second_inode)
        assert stat_nlink(path1_real_file) == 1

        os.unlink(path1_real_file)
        assert not lexists(path1_real_file)

    def test_soft_link(self):
        path1_real_file = join(self.test_dir, 'path1_real_file')
        path2_symlink = join(self.test_dir, 'path2_symlink')
        touch(path1_real_file)
        assert isfile(path1_real_file)
        assert not islink(path1_real_file)

        symlink(path1_real_file, path2_symlink)
        assert exists(path2_symlink)
        assert lexists(path2_symlink)
        assert islink(path2_symlink)

        assert readlink(path2_symlink).endswith(path1_real_file)
        # for win py27, readlink actually gives something that starts with \??\
        # \??\c:\users\appveyor\appdata\local\temp\1\c571cb0c\path1_real_file

        assert stat_nlink(path1_real_file) == stat_nlink(path2_symlink) == 1

        os.unlink(path1_real_file)
        assert not isfile(path1_real_file)
        assert not lexists(path1_real_file)
        assert not exists(path1_real_file)

        assert lexists(path2_symlink)
        if not (on_win and PY2):
            # I guess I'm not surprised this exist vs lexist is different for win py2
            #   consider adding a fix in the future
            assert not exists(path2_symlink)

        os.unlink(path2_symlink)
        assert not lexists(path2_symlink)
        assert not exists(path2_symlink)
