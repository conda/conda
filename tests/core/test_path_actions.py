# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os.path import basename, isdir, join, lexists, isfile
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

from conda.core.path_actions import LinkPathAction
from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.models.enums import LinkType

log = getLogger(__name__)


def make_test_file(target_dir):
    fn = str(uuid4())[:8]
    full_path = join(target_dir, fn)
    with open(full_path, 'w') as fh:
        fh.write(str(uuid4()))
    return full_path


class PathActionsTests(TestCase):

    def setUp(self):
        tempdirdir = gettempdir()

        prefix_dirname = str(uuid4())[:8]
        self.prefix = join(tempdirdir, prefix_dirname)
        mkdir_p(self.prefix)
        assert isdir(self.prefix)

        pkgs_dirname = str(uuid4())[:8]
        self.pkgs_dir = join(tempdirdir, pkgs_dirname)
        mkdir_p(self.pkgs_dir)
        assert isdir(self.pkgs_dir)

    def tearDown(self):
        rm_rf(self.prefix)
        assert not lexists(self.prefix)
        rm_rf(self.pkgs_dir)
        assert not lexists(self.pkgs_dir)

    def test_CompilePycAction(self):
        # transaction_context = dict()
        # python_version = UnlinkLinkTransaction.get_python_version(self.target_prefix,
        #                                          self.linked_packages_data_to_unlink,
        #                                          self.packages_info_to_link)
        # transaction_context['target_python_version'] = python_version
        # sp = get_python_site_packages_short_path(python_version)
        # transaction_context['target_site_packages_short_path'] = sp


        # # transaction_context, package_info, target_prefix, requested_link_type, file_link_actions
        # axns = CompilePycAction.create_actions(transaction_context, package_info, target_prefix, requested_link_type, file_link_actions)
        # axn = CompilePycAction(transaction_context, package_info, target_prefix, source_short_path, target_short_path)
        pass

    def test_simple_LinkPathAction_hardlink(self):
        source_full_path = make_test_file(self.pkgs_dir)
        target_short_path = source_short_path = basename(source_full_path)
        axn = LinkPathAction({}, None, self.pkgs_dir, source_short_path, self.prefix,
                             target_short_path, LinkType.hardlink)

        assert axn.target_full_path == join(self.prefix, target_short_path)
        axn.verify()
        axn.execute()
        assert isfile(axn.target_full_path)
        # assert not islink(axn.target_full_path)

        axn.reverse()
        assert not lexists(axn.target_full_path)

    def test_simple_LinkPathAction_softlink(self):
        pass

    def test_simple_LinkPathAction_directory(self):
        pass

    def test_simple_LinkPathAction_copy(self):
        source_full_path = make_test_file(self.pkgs_dir)
        target_short_path = source_short_path = basename(source_full_path)
        axn = LinkPathAction({}, None, self.pkgs_dir, source_short_path, self.prefix,
                             target_short_path, LinkType.copy)

        assert axn.target_full_path == join(self.prefix, target_short_path)
        axn.verify()
        axn.execute()
        assert isfile(axn.target_full_path)
        # assert not islink(axn.target_full_path)

        axn.reverse()
        assert not lexists(axn.target_full_path)
