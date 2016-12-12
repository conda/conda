from conda.models.channel import Channel
from conda.models.package_info import PackageInfo, PathData, PathType, Noarch
from conda.models.enums import FileMode, PathType
from conda.models.record import Record
from unittest import TestCase


class DefaultPackageInfo(TestCase):
    def test_package_info(self):
        index_json_record = Record(build=0, build_number=0, name="test_foo", version=0)
        icondata = "icondata"
        noarch = Noarch(type="python", entry_points=["test:foo"])
        paths = [PathData(_path="test/path/1", file_mode=FileMode.text, path_type=PathType.hardlink,
                          prefix_placeholder="/opt/anaconda1anaconda2anaconda3", ),
                 PathData(_path="test/path/2", no_link=True, path_type=PathType.hardlink),
                 PathData(_path="test/path/3", path_type=PathType.softlink),
                 PathData(_path="menu/test.json", path_type=PathType.hardlink)]

        package_info = PackageInfo(extracted_package_dir='/some/path',
                                   channel=Channel('defaults'),
                                   repodata_record=index_json_record,
                                   url='https://some.com/place/file.tar.bz2',
                                   paths_version=0,
                                   paths=paths,
                                   index_json_record=index_json_record,
                                   icondata=icondata,
                                   noarch=noarch)

        self.assertIsInstance(package_info.paths[0], PathData)
        self.assertIsInstance(package_info.index_json_record, Record)
        self.assertIsInstance(package_info.noarch, Noarch)
        self.assertEquals(package_info.paths[0].path, "test/path/1")
