"""
The strategy for checking file permissions is as follows:
 - turn the list of files into a convenient data structure of the form:
    { "root": [("dir", "d"), ("file.txt", "f")],
        "dir": [("dir/foo", "d"), ("dir/bar.txt", "f")],
        "dir/foo": [("dir/foo/baz.txt", "f")]
    }
    where
        - there always exists a root key that has all the highest level directories
        - there are a list of tuples of the form (<name>, <d if directory, f if file>)
 - start from the root directory and grab the children. For each child; determine if you are
   dealing with a file or a directory.
    - if it's a file;
        - ensure that it does not currently exist in the prefix OR will be unlinked
    - if it's a directory;
        - check if it exists
            - if it exists; move on to checking it's children
            - if it does not exist; ensure that you can write to it's parent directory
"""

from .exceptions import CondaFileIOError
from os.path import join, dirname
from os import W_OK
import os
from .utils import on_win

# file types
DIR = "d"
FILE = "f"


class FilePermissions(object):

    def __init__(self, prefix):
        self.prefix = prefix

    def _compose_file_structure(self, files):
        file_structure = {"root": []}
        for f in files:
            file_elements = f.split("/")
            abs_depth = len(file_elements)
            for el in file_elements:
                depth = file_elements.index(el)
                el_type = FILE if depth+1 == abs_depth else DIR
                path = "/".join(file_elements[0:depth])
                child_path = "/".join(file_elements[0:depth + 1])
                child_node = (child_path, el_type)
                if depth == 0:
                    root_el = (el, el_type)
                    if root_el not in file_structure.get("root"):
                        file_structure["root"].append((el, el_type))
                elif depth < abs_depth:
                    existing_child_nodes = file_structure.get(path)
                    if path in file_structure.keys() and child_node not in existing_child_nodes:
                        existing_child_nodes.append(child_node)
                    elif path not in file_structure.keys():
                        file_structure[path] = [child_node]
        return file_structure

    def _check_file(self, path, unlink_files):
        is_being_unlinked = path in unlink_files
        if not os.path.exists(path) or is_being_unlinked:
            self.check_write_permission(dirname(path))
        else:
            raise CondaFileIOError(path, "File already exists, cannot link")

    def _check_dir(self, dst, structured_link_files, unlink_files):
        path = join(self.prefix, dst)
        if os.path.exists(path):
            self._check_files_permissions(structured_link_files, dst, unlink_files)
        else:
            self.check_write_permission(dirname(path))

    def _check_files_permissions(self, structured_link_files, structured_files_root, unlink_files):
        paths = structured_link_files.get(structured_files_root)
        for path in paths:
            if path[1] == DIR:
                self._check_dir(path[0], structured_link_files, unlink_files)
            elif path[1] == FILE:
                self._check_file(join(self.prefix, path[0]), unlink_files)

    def _can_write(self, path):
        # On windows, "modify" permission is required on directories and files. This means that the
        # user is able to create, rename, write to and delete files or directories
        if not os.path.exists(path):
            return False
        if os.path.isdir(path):
            test_file = join(path, "tmp-check-write-perms")
            try:
                open(test_file, 'a').close()
                os.remove(test_file)
            except IOError:
                return False
        elif os.path.isfile(path):
            try:
                # Updates the access and modified times of path to the current time
                os.utime(path, times=None)
            except IOError:
                return False
        return True

    def check_write_permission(self, path):
        """
            Check if the path is writable
        :param path: the path of interest
        :return: True if the path is writeable
        """
        if on_win:
            w_permission = self._can_write(path)
        else:
            w_permission = os.access(path, W_OK)

        if not w_permission:
            raise CondaFileIOError(path, "Cannot write to path %s" % path)
        return True

    def check(self, link_files, unlink_files):
        """
            Walks down the file path to ensure that conda has the correct permissions to link files
        :param link_files: A list of files that are going to be linked by the plan
        :param unlink_files: A list of files that are going to be unlinked by the plan
        :return:
        """
        self._check_files_permissions(
            self._compose_file_structure(link_files), "root", unlink_files)
        return True
