import pytest
import unittest
import sys
from os.path import join
import os
from shutil import rmtree

from conda import noarch

try:
    from unittest.mock import patch, Mock
except ImportError:
    from mock import patch, Mock


def stub_sys_platform(platform):
    def sys_platform(func):
        def func_wrapper(plat):
            sys_plat = sys.platform
            sys.platform = platform
            func(plat)
            sys.platform = sys_plat
        return func_wrapper
    return sys_platform


def setup_info_dir(info_dir):
    entry_point_info = '{"type": "python", "entry_points": ["cmd = module.foo:func"]}'
    with open(join(info_dir, "noarch.json"), "w") as noarch_json:
        noarch_json.write(entry_point_info)


def setup_env_for_linkning(prefix):
    src_dir = join(os.path.dirname(__file__), "src_test")
    info_dir = join(src_dir, "info")
    os.mkdir(src_dir)
    os.mkdir(info_dir)

    setup_info_dir(info_dir)

    os.mkdir(join(src_dir, "python-scripts"))
    os.mkdir(join(src_dir, "site-packages"))
    os.mkdir(join(prefix, 'conda-meta'))

    open(join(src_dir, "python-scripts/test3"), 'a').close()
    open(join(src_dir, "site-packages/test2"), 'a').close()

    file_content = ["test1", "dir/site-packages/test2", "bin/test3"]
    with open(join(info_dir, "files"), "w") as f:
        for content in file_content:
            f.write("%s\n" % content)


def tear_down_env_for_linking(prefix):
    src_dir = join(os.path.dirname(__file__), "src_test")
    info_dir = join(src_dir, "info")
    rmtree(info_dir)
    rmtree(src_dir)
    rmtree(join(prefix, "conda-meta"))


class TestHelpers(unittest.TestCase):

    def test_get_noarch_cls(self):
        self.assertEquals(noarch.get_noarch_cls("python"), noarch.NoArchPython)
        self.assertEquals(noarch.get_noarch_cls("none"), noarch.NoArch)
        self.assertEquals(noarch.get_noarch_cls(True), noarch.NoArch)
        self.assertEquals(noarch.get_noarch_cls(None), None)

    @stub_sys_platform("win32")
    def test_get_site_packages_dir_win(self):
        site_packages_dir = noarch.get_site_packages_dir("")
        self.assertEquals(site_packages_dir, "Lib")

    @stub_sys_platform("darwin")
    def test_get_site_packages_dir_unix(self):
        with patch.object(noarch, "get_python_version_for_prefix", return_value="3.5") as m:
            site_packages_dir = noarch.get_site_packages_dir("")
            self.assertEquals(site_packages_dir, 'lib/python3.5')

    @stub_sys_platform("win32")
    def test_get_bin_dir_win(self):
        bin_dir = noarch.get_bin_dir("")
        self.assertEquals(bin_dir, "Scripts")

    @stub_sys_platform("darwin")
    def test_get_bin_dir_unix(self):
        bin_dir = noarch.get_bin_dir("")
        self.assertEquals(bin_dir, "bin")

    @patch("conda.noarch.get_python_version_for_prefix", return_value="2")
    @patch("subprocess.call")
    def test_compile_missing_pyc(self, get_python_version, subprocess_call):
        noarch.compile_missing_pyc("", ["test.py"], "")
        subprocess_call.called_with(["python", '-Wi', '-m', 'py_compile', "test.py"], cwd="")


class TestEntryPointCreation(unittest.TestCase):

    def setUp(self):
        config = Mock()
        config.info_dir = join(os.path.dirname(__file__), "info")
        os.mkdir(config.info_dir)
        setup_info_dir(config.info_dir)

    def tearDown(self):
        rmtree(join(os.path.dirname(__file__), "info"))

    @stub_sys_platform("darwin")
    def test_create_entry_points_unix(self):
        src_dir = os.path.dirname(__file__)
        bin_dir = join(os.path.dirname(__file__), "tmp_bin")
        entry_point = join(bin_dir, "cmd")
        os.mkdir(bin_dir)
        prefix = ""
        entry_point_content = """\
#!bin/python
if __name__ == '__main__':
    import sys
    import module.foo

    sys.exit(module.foo.func())
"""

        noarch.create_entry_points(src_dir, bin_dir, prefix)
        self.assertTrue(os.path.isfile(entry_point))
        with open(entry_point, 'r') as script:
            data = script.read()
            self.assertEqual(data, entry_point_content)
        rmtree(bin_dir)

    @stub_sys_platform("win32")
    def test_create_entry_points_win(self):
        src_dir = os.path.dirname(__file__)
        bin_dir = join(os.path.dirname(__file__), "tmp_bin")
        entry_point = join(bin_dir, "cmd-script.py")
        os.mkdir(bin_dir)
        cli_script_src = join(src_dir, 'cli-64.exe')
        cli_script_dst = join(bin_dir, "cmd.exe")
        open(cli_script_src, 'a').close()
        prefix = ""
        entry_point_content = """\
if __name__ == '__main__':
    import sys
    import module.foo

    sys.exit(module.foo.func())
"""

        noarch.create_entry_points(src_dir, bin_dir, prefix)
        self.assertTrue(os.path.isfile(entry_point))
        self.assertTrue(os.path.isfile(cli_script_dst))
        with open(entry_point, 'r') as script:
            data = script.read()
            self.assertEqual(data, entry_point_content)
        rmtree(bin_dir)
        os.remove(cli_script_src)


class TestEntryLinkFiles(unittest.TestCase):

    def setUp(self):
        src_root = join(os.path.dirname(__file__), "src_test")
        dst_root = join(os.path.dirname(__file__), "dst_test")
        os.mkdir(src_root)
        os.mkdir(dst_root)
        open(join(src_root, "testfile1"), 'a').close()
        open(join(src_root, "testfile2"), 'a').close()

    def tearDown(self):
        src_root = join(os.path.dirname(__file__), "src_test")
        dst_root = join(os.path.dirname(__file__), "dst_test")
        rmtree(src_root)
        rmtree(dst_root)

    def check_files(self, files, dst_root, dst_files):
        for f in files:
            dst_file = join(dst_root, f)
            self.assertTrue(os.path.isfile(dst_file))
            self.assertTrue(dst_files.index(dst_file) >= 0)
            os.remove(dst_file)

    def test_link(self):
        prefix = os.path.dirname(__file__)
        src_root = join(os.path.dirname(__file__), "src_test")
        dst_root = join(os.path.dirname(__file__), "dst_test")
        files = ["testfile1", "testfile2"]

        dst_files = noarch.link_files(prefix, src_root, dst_root, files, src_root)
        self.check_files(files, dst_root, dst_files)

    def test_requires_mkdir(self):
        prefix = os.path.dirname(__file__)
        src_root = join(os.path.dirname(__file__), "src_test")
        dst_root = join(os.path.dirname(__file__), "dst_test/not_exist")
        files = ["testfile1", "testfile2"]

        dst_files = noarch.link_files(prefix, src_root, dst_root, files, src_root)
        self.check_files(files, dst_root, dst_files)

    def test_file_already_exists(self):
        prefix = os.path.dirname(__file__)
        src_root = join(os.path.dirname(__file__), "src_test")
        dst_root = join(os.path.dirname(__file__), "dst_test")
        files = ["testfile1", "testfile2"]
        open(join(dst_root, "testfile1"), 'a').close()

        dst_files = noarch.link_files(prefix, src_root, dst_root, files, src_root)
        self.check_files(files, dst_root, dst_files)


class TestNoArch(unittest.TestCase):

    def test_link(self):
        pass


class TestNoArchPythonWindowsLink(unittest.TestCase):

    def setUp(self):
        prefix = join(os.path.dirname(__file__), "test-dir")
        os.mkdir(prefix)
        setup_env_for_linkning(prefix)
        os.mkdir(join(prefix, "Lib"))
        os.mkdir(join(prefix, "Lib/site-packages"))
        os.mkdir(join(prefix, "Scripts"))

    def tearDown(self):
        prefix = join(os.path.dirname(__file__), "test-dir")
        tear_down_env_for_linking(prefix)
        rmtree(join(prefix, "Lib"))
        rmtree(join(prefix, "Scripts"))
        rmtree(prefix)

    @stub_sys_platform("win32")
    @patch("conda.install.dist2filename", return_value="test.files")
    def test_link(self, dist2filename):
        prefix = join(os.path.dirname(__file__), "test-dir")

        with patch.object(noarch, "get_python_version_for_prefix", return_value="3.5") as m:
            src_dir = join(os.path.dirname(__file__), "src_test")
            noarch.NoArchPython().link(prefix, src_dir, "dist-test")

        alt_files_path = join(prefix, "conda-meta/test.files")
        self.assertTrue(os.path.isfile(alt_files_path))
        with open(alt_files_path, "r") as alt_files:
            files = alt_files.read().split("\n")[:-1]

        self.assertTrue(files.index("Lib/site-packages/test2") >= 0)
        self.assertTrue(files.index("Scripts/test3") >= 0)
        self.assertTrue(os.path.isfile(join(prefix, "Lib/site-packages/test2")))
        self.assertTrue(os.path.isfile(join(prefix, "Scripts/test3")))


class TestNoArchPythonUnixLink(unittest.TestCase):

    def setUp(self):
        prefix = join(os.path.dirname(__file__), "test-dir")
        os.mkdir(prefix)
        setup_env_for_linkning(prefix)
        os.mkdir(join(prefix, "lib"))
        os.mkdir(join(prefix, "lib/python3.5"))
        os.mkdir(join(prefix, "lib/python3.5/site-packages"))
        os.mkdir(join(prefix, "bin"))

    def tearDown(self):
        prefix = join(os.path.dirname(__file__), "test-dir")
        tear_down_env_for_linking(prefix)
        rmtree(join(prefix, "lib"))
        rmtree(join(prefix, "bin"))
        rmtree(prefix)

    @stub_sys_platform("darwin")
    @patch("conda.install.dist2filename", return_value="test.files")
    def test_link(self, dist2filename):
        prefix = join(os.path.dirname(__file__), "test-dir")
        with patch.object(noarch, "get_python_version_for_prefix", return_value="3.5") as m:
            src_dir = join(os.path.dirname(__file__), "src_test")
            noarch.NoArchPython().link(prefix, src_dir, "dist-test")

        alt_files_path = join(prefix, "conda-meta/test.files")
        self.assertTrue(os.path.isfile(alt_files_path))
        with open(alt_files_path, "r") as alt_files:
            files = alt_files.read().split("\n")[:-1]

        self.assertTrue(files.index("lib/python3.5/site-packages/test2") >= 0)
        self.assertTrue(files.index("bin/test3") >= 0)
        self.assertTrue(os.path.isfile(join(prefix, "lib/python3.5/site-packages/test2")))
        self.assertTrue(os.path.isfile(join(prefix, "bin/test3")))
