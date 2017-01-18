import os
from conda.compat import TemporaryDirectory
from conda.common.disk import rm_rf


def test_rm_rf_does_not_follow_symlinks():
    with TemporaryDirectory() as tmp:
        # make a file in some temp folder
        real_file = os.path.join(tmp, 'testfile')
        with open(real_file, 'w') as f:
            f.write('weee')
        # make a subfolder
        subdir = os.path.join(tmp, 'subfolder')
        os.makedirs(subdir)
        # link to the file in the subfolder
        os.symlink(real_file, os.path.join(subdir, 'file_link'))
        # rm_rf the subfolder
        rm_rf(subdir)
        # assert that the file still exists in the root folder
        assert os.path.isfile(real_file)
