import os

from conda.core import package_cache_data as pcd
from conda.exports import url_path
from conda.core.index import get_index

CONDA_PKG_REPO = url_path(os.path.join(os.path.dirname(__file__), '..', 'data', 'conda_format_repo'))


def test_ProgressiveFetchExtract_prefers_conda_v2_format():
    index = get_index([CONDA_PKG_REPO], prepend=False)
    rec = next(iter(index))
    cache_action, extract_action = pcd.ProgressiveFetchExtract.make_actions_for_record(rec)

    assert cache_action.target_package_basename.endswith('.conda')
    assert cache_action.sha256sum == rec.conda_outer_sha256
    assert cache_action.expected_size_in_bytes == rec.conda_size

    assert extract_action.source_full_path.endswith('.conda')
    assert extract_action.sha256sum == rec.conda_outer_sha256
