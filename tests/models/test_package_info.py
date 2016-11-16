from conda.models.package_info import PackageInfo, PathInfo, NodeType, NoarchInfo
from conda.base.constants import FileMode
from conda.models.record import Record
from unittest import TestCase


class DefaultPackageInfo(TestCase):
    def test_package_info(self):
        index_json_records = Record(build=0, build_number=0, name="test_foo", version=0)
        icondata = "icondata"
        noarch = NoarchInfo(type="python", entry_points=["test:foo"])
        files = [PathInfo(path="test/path/1", file_mode=FileMode.text, node_type=NodeType.hardlink,
                          prefix_placeholder="/opt/anaconda1anaconda2anaconda3", ),
                 PathInfo(path="test/path/2", no_link=True, node_type=NodeType.hardlink),
                 PathInfo(path="test/path/3", node_type=NodeType.softlink),
                 PathInfo(path="menu/test.json", node_type=NodeType.hardlink)]

        package_info = PackageInfo(path_info_version=0, files=files, icondata=icondata,
                                   index_json_record=index_json_records, noarch=noarch)
        self.assertIsInstance(package_info.files[0], PathInfo)
        self.assertIsInstance(package_info.index_json_record, Record)
        self.assertIsInstance(package_info.noarch, NoarchInfo)
        self.assertEquals(package_info.files[0].path, "test/path/1")
