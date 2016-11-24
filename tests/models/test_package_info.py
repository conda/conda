from conda.models.package_info import PackageInfo, PathInfo, PathType, NoarchInfo
from conda.base.constants import FileMode
from conda.models.record import Record
from unittest import TestCase


class DefaultPackageInfo(TestCase):
    def test_package_info(self):
        index_json_records = Record(build=0, build_number=0, name="test_foo", version=0)
        icondata = "icondata"
        noarch = NoarchInfo(type="python", entry_points=["test:foo"])
        paths = [PathInfo(_path="test/path/1", file_mode=FileMode.text, path_type=PathType.hardlink,
                          prefix_placeholder="/opt/anaconda1anaconda2anaconda3", ),
                 PathInfo(_path="test/path/2", no_link=True, path_type=PathType.hardlink),
                 PathInfo(_path="test/path/3", path_type=PathType.softlink),
                 PathInfo(_path="menu/test.json", path_type=PathType.hardlink)]

        package_info = PackageInfo(paths_version=0, paths=paths, icondata=icondata,
                                   index_json_record=index_json_records, noarch=noarch)
        self.assertIsInstance(package_info.paths[0], PathInfo)
        self.assertIsInstance(package_info.index_json_record, Record)
        self.assertIsInstance(package_info.noarch, NoarchInfo)
        self.assertEquals(package_info.paths[0].path, "test/path/1")
