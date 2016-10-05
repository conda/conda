import unittest
from os.path import dirname, join
from conda.file_permissions import FilePermissions
from conda.exceptions import CondaFileIOError

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


class TestFilePermissions(unittest.TestCase):

    def test_check_write_permissions_real_path(self):
        permission = FilePermissions("").check_write_permission(dirname(__file__))
        self.assertTrue(permission)

    def test_check_write_permissions_non_existent_path(self):
        path = join(dirname(__file__), "test-permission")
        permission = FilePermissions("").check_write_permission(path)
        self.assertTrue(permission)

    @patch("os.access", return_value=False)
    def test_check_write_permissions_no_permissions(self, os_access):
        path = join(dirname(__file__), "test-permission")
        try:
            FilePermissions("").check_write_permission(path)
        except CondaFileIOError as e:
            self.assertEquals(type(e), CondaFileIOError)
        else:
            self.fail('CondaFileIOError not raised')

    def test_compose_file_structure(self):
        link_list = ["etc/es.yml", "etc/nginx/nginx.conf", "etc/nginx/conf.d/mysite.conf",
                     "etc/redis/redis.conf", "etc/redis/conf.d/myredis.conf", "rando.txt"]
        expected_file_structure = {
            "root": [("etc", "d"), ("rando.txt", "f")],
            "etc": [("etc/es.yml", "f"), ("etc/nginx", "d"), ("etc/redis", "d")],
            "etc/nginx": [("etc/nginx/nginx.conf", "f"), ("etc/nginx/conf.d", "d")],
            "etc/redis": [("etc/redis/redis.conf", "f"), ("etc/redis/conf.d", "d")],
            "etc/nginx/conf.d": [("etc/nginx/conf.d/mysite.conf", "f")],
            "etc/redis/conf.d": [("etc/redis/conf.d/myredis.conf", "f")],
        }
        structured_files = FilePermissions("")._compose_file_structure(link_list)
        self.assertListEqual(
            sorted(expected_file_structure.keys()),
            sorted(structured_files.keys()))
        for key in expected_file_structure.keys():
            self.assertListEqual(expected_file_structure.get(key), structured_files.get(key))

    # @patch("os.path.exists", return_value=True)
    # @patch("conda.instructions.check_write_permission", return_value=True)
    # def test_check_file_exists_and_unlink(self, check_write_permissions, exists):
    #     self.assertTrue(instructions.check_file("foo/bar", ["foo/bar"]))
    #     check_write_permissions.assert_called_once_with("foo")
    #
    # @patch("os.path.exists", return_value=True)
    # @patch("conda.instructions.check_write_permission", return_value=True)
    # def test_check_file_exists_and_not_unlink(self, check_write_permissions, exists):
    #     with self.assertRaises(CondaFileIOError):
    #         instructions.check_file("foo/bar", ["foo/baz"])
    #
    # @patch("os.path.exists", return_value=False)
    # @patch("conda.instructions.check_write_permission", return_value=True)
    # def test_check_file_not_exists_and_not_unlink(self, check_write_permissions, exists):
    #     self.assertTrue(instructions.check_file("foo/bar", ["foo/baz"]))
    #     check_write_permissions.assert_called_once_with("foo")
    #
    # @patch("os.path.exists", return_value=False)
    # @patch("conda.instructions.check_write_permission", return_value=True)
    # def test_check_file_not_exists_and_unlink(self, check_write_permissions, exists):
    #     self.assertTrue(instructions.check_file("foo/bar", ["foo/bar"]))
    #     check_write_permissions.assert_called_once_with("foo")
    #
    # @patch("os.path.exists", return_value=True)
    # @patch("conda.instructions.check_files_permissions")
    # def test_check_dir_path_exists(self, check_file_permissions, exists):
    #     self.assertTrue(instructions.check_dir("", "", {}, []))
    #     check_file_permissions.assert_called_once_with("", {}, "", [])
    #
    # @patch("os.path.exists", return_value=False)
    # @patch("conda.instructions.check_write_permission", return_value=True)
    # def test_check_dir_path_not_exists(self, check_write_permissions, exists):
    #     self.assertTrue(instructions.check_dir("foo", "bar", {}, []))
    #     check_write_permissions.assert_called_once_with("bar")
    #
    # @patch("os.path.exists", return_value=False)
    # @patch("conda.instructions.check_write_permission", return_value=True)
    # def test_check_files_permission(self, check_write_permission, exists):
    #     link_list = ["etc/es.yml", "etc/nginx/nginx.conf", "etc/nginx/conf.d/mysite.conf",
    #                  "etc/redis/redis.conf", "etc/redis/conf.d/myredis.conf", "rando.txt"]
    #     unlink_list = ["etc/nginx/nginx.conf"]
    #     instructions.check_files_permissions(
    #         "", instructions.compose_file_structure(link_list), "root", unlink_list)
