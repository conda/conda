# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.base.context import context
from conda.models.channel import Channel
from conda.models.enums import FileMode, PathEnum
from conda.models.package_info import Noarch, PackageInfo, PackageMetadata
from conda.models.records import PackageRecord, PathDataV1, PathsData


def test_package_info():
    index_json_record = PackageRecord(
        build=0,
        build_number=0,
        name="test_foo",
        version=0,
        channel="defaults",
        subdir=context.subdir,
        fn="doesnt-matter",
        md5="0123456789",
    )
    icondata = "icondata"
    package_metadata = PackageMetadata(
        package_metadata_version=1,
        noarch=Noarch(type="python", entry_points=["test:foo"]),
    )

    paths = [
        PathDataV1(
            _path="test/path/1",
            file_mode=FileMode.text,
            path_type=PathEnum.hardlink,
            prefix_placeholder="/opt/anaconda1anaconda2anaconda3",
        ),
        PathDataV1(_path="test/path/2", no_link=True, path_type=PathEnum.hardlink),
        PathDataV1(_path="test/path/3", path_type=PathEnum.softlink),
        PathDataV1(_path="menu/test.json", path_type=PathEnum.hardlink),
    ]
    paths_data = PathsData(paths_version=0, paths=paths)

    package_info = PackageInfo(
        extracted_package_dir="/some/path",
        package_tarball_full_path="/some/path.tar.bz2",
        channel=Channel("defaults"),
        repodata_record=index_json_record,
        url="https://some.com/place/path.tar.bz2",
        index_json_record=index_json_record,
        icondata=icondata,
        package_metadata=package_metadata,
        paths_data=paths_data,
    )

    assert isinstance(package_info.paths_data.paths[0], PathDataV1)
    assert isinstance(package_info.package_metadata.noarch, Noarch)
    assert package_info.paths_data.paths[0].path == "test/path/1"
