# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import unittest
import pytest
import os
import shutil
import tempfile

from .test_create import run_command, Commands

from conda_build import api

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)

def build_package(package_path):
    output = api.build(package_path, need_source_download=False)
    return output

class TestLinkOrder(unittest.TestCase):
    def setUp(self):
        thisdir = os.path.dirname(os.path.realpath(__file__))
        self.recipe_dir = os.path.join(thisdir, 'test-recipes')
        self.prefix = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.prefix)


    @pytest.mark.integration
    def test_link_order_post_link_actions(self):
        recipes = tuple(["b_post_link_package", "c_post_link_package"])
        for recipe in recipes:
            build_package(os.path.join(self.recipe_dir, recipe))
        stdout, stderr = run_command(Commands.CREATE, self.prefix, "c_post_link_package --use-local")
        assert(stderr == '')

    @pytest.mark.integration
    def test_link_order_post_link_depend(self):
        recipes = tuple(["d_post_link_package", "e_post_link_package"])
        for recipe in recipes:
            build_package(os.path.join(self.recipe_dir, recipe))
        stdout, stderr = run_command(Commands.CREATE, self.prefix, "e_post_link_package --use-local")
        assert(stderr == '')
