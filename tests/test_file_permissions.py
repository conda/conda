# import unittest
# from os.path import dirname, join
# from conda import file_permissions
# from conda.file_permissions import FilePermissions
# from conda.exceptions import CondaFileIOError
#
# try:
#     from unittest.mock import patch, call
# except ImportError:
#     from mock import patch, call
#
#
# class TestFilePermissions(unittest.TestCase):
#
#     def test_check_write_permissions_real_path(self):
#         permission = FilePermissions("").check_write_permission(dirname(__file__))
#         self.assertTrue(permission)
#
#     def test_check_write_permissions_non_existent_path(self):
#         path = join(dirname(__file__), "test-permission")
#         try:
#             FilePermissions("").check_write_permission(path)
#         except CondaFileIOError as e:
#             self.assertEquals(type(e), CondaFileIOError)
#         else:
#             self.fail('CondaFileIOError not raised')
#
#     @patch("os.access", return_value=False)
#     @patch("conda.file_permissions.FilePermissions._can_write", return_value=False)
#     def test_check_write_permissions_no_permissions(self, _can_write, os_access):
#         path = join(dirname(__file__), "test-permission")
#         try:
#             FilePermissions("").check_write_permission(path)
#         except CondaFileIOError as e:
#             self.assertEquals(type(e), CondaFileIOError)
#         else:
#             self.fail('CondaFileIOError not raised')
#
#     def test_compose_file_structure(self):
#         link_list = ["etc/es.yml", "etc/nginx/nginx.conf", "etc/nginx/conf.d/mysite.conf",
#                      "etc/redis/redis.conf", "etc/redis/conf.d/myredis.conf", "rando.txt"]
#         expected_file_structure = {
#             "root": [("etc", "d"), ("rando.txt", "f")],
#             "etc": [("etc/es.yml", "f"), ("etc/nginx", "d"), ("etc/redis", "d")],
#             "etc/nginx": [("etc/nginx/nginx.conf", "f"), ("etc/nginx/conf.d", "d")],
#             "etc/redis": [("etc/redis/redis.conf", "f"), ("etc/redis/conf.d", "d")],
#             "etc/nginx/conf.d": [("etc/nginx/conf.d/mysite.conf", "f")],
#             "etc/redis/conf.d": [("etc/redis/conf.d/myredis.conf", "f")],
#         }
#         structured_files = FilePermissions("")._compose_file_structure(link_list)
#         self.assertListEqual(
#             sorted(expected_file_structure.keys()),
#             sorted(structured_files.keys()))
#         for key in expected_file_structure.keys():
#             self.assertListEqual(expected_file_structure.get(key), structured_files.get(key))
#
#     @patch("os.path.exists", return_value=False)
#     @patch("conda.file_permissions.FilePermissions.check_write_permission", return_value=True)
#     def test_check_path_clear(self, check_write_permission, exists):
#         link_list = ["etc/es.yml", "etc/nginx/nginx.conf", "etc/nginx/conf.d/mysite.conf",
#                      "etc/redis/redis.conf", "etc/redis/conf.d/myredis.conf", "rando.txt"]
#         unlink_list = ["etc/es.yml", "etc/nginx/nginx.conf", "etc/nginx/conf.d/mysite.conf",
#                      "etc/redis/redis.conf", "etc/redis/conf.d/myredis.conf", "rando.txt"]
#         self.assertTrue(FilePermissions("").check(link_list, unlink_list))
#         exist_calls = [call("rando.txt"), call("etc")]
#         exists.assert_has_calls(exist_calls, any_order=True)
#         check_write_permission.assert_called_with("")
#
#     @patch("os.path.exists", return_value=True)
#     @patch("conda.file_permissions.FilePermissions.check_write_permission", return_value=True)
#     def test_check_follows_tree(self, check_write_permission, exists):
#         link_list = ["etc/es.yml", "etc/nginx/nginx.conf", "etc/nginx/conf.d/mysite.conf",
#                      "etc/redis/redis.conf", "etc/redis/conf.d/myredis.conf", "rando.txt"]
#         unlink_list = ["etc/es.yml", "etc/nginx/nginx.conf", "etc/nginx/conf.d/mysite.conf",
#                      "etc/redis/redis.conf", "etc/redis/conf.d/myredis.conf", "rando.txt"]
#         self.assertTrue(FilePermissions("").check(link_list, unlink_list))
#         exist_calls = []
#         for link in link_list:
#             exist_calls.append(call(link))
#         exists.assert_has_calls(exist_calls, any_order=True)
#         check_write_permission_calls = [
#             call("etc"), call("etc/nginx"), call("etc/redis"), call("etc/nginx/conf.d"),
#             call("etc/redis/conf.d")]
#         check_write_permission.assert_has_calls(check_write_permission_calls, any_order=True)
#
#     @patch("os.path.exists", return_value=False)
#     @patch("conda.file_permissions.FilePermissions.check_write_permission", return_value=True)
#     def test_check_no_unlinking_and_path_clear(self, check_write_permission, exists):
#         link_list = ["etc/es.yml", "etc/nginx/nginx.conf", "etc/nginx/conf.d/mysite.conf",
#                      "etc/redis/redis.conf", "etc/redis/conf.d/myredis.conf", "rando.txt"]
#         unlink_list = []
#         self.assertTrue(FilePermissions("").check(link_list, unlink_list))
#         exist_calls = [call("rando.txt"), call("etc")]
#         exists.assert_has_calls(exist_calls, any_order=True)
#         check_write_permission.assert_called_with("")
#
#     @patch("os.path.exists", return_value=True)
#     @patch("conda.file_permissions.FilePermissions.check_write_permission", return_value=True)
#     def test_check_no_unlinking_and_follows_tree(self, check_write_permission, exists):
#         link_list = ["etc/es.yml", "etc/nginx/nginx.conf", "etc/nginx/conf.d/mysite.conf",
#                      "etc/redis/redis.conf", "etc/redis/conf.d/myredis.conf"]
#         unlink_list = []
#         try:
#             FilePermissions("").check(link_list, unlink_list)
#         except CondaFileIOError as e:
#             self.assertEquals(type(e), CondaFileIOError)
#         else:
#             self.fail('CondaFileIOError not raised')
#         exists.assert_called_with("etc/es.yml")
#
#     @patch("os.path.exists", return_value=False)
#     @patch("os.access", return_value=False)
#     @patch("conda.file_permissions.FilePermissions._can_write", return_value=False)
#     def test_check_no_access(self, _can_write, access, exists):
#         link_list = ["etc/es.yml", "etc/nginx/nginx.conf", "etc/nginx/conf.d/mysite.conf",
#                      "etc/redis/redis.conf", "etc/redis/conf.d/myredis.conf", "rando.txt"]
#         unlink_list = []
#         try:
#             FilePermissions("").check(link_list, unlink_list)
#         except CondaFileIOError as e:
#             self.assertEquals(type(e), CondaFileIOError)
#             self.assertEquals(e.filepath, "")
#         else:
#             self.fail('CondaFileIOError not raised')
#
#     def test_check_no_link_files(self):
#         self.assertTrue(FilePermissions("").check([], []))
