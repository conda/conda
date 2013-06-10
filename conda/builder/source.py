import os
import sys
from subprocess import check_call, Popen, PIPE
from os.path import join, isdir, isfile

from config import croot
from utils import download, md5_file, rm_rf, tar_xf, unzip


SRC_CACHE = join(croot, 'src_cache')
GIT_CACHE = join(croot, 'git_cache')
WORK_DIR = join(croot, 'work')


def get_dir():
    lst = [fn for fn in os.listdir(WORK_DIR) if not fn.startswith('.')]
    if len(lst) == 1:
        dir_path = join(WORK_DIR, lst[0])
        if isdir(dir_path):
            return dir_path
    return WORK_DIR


def download_to_cache(meta):
    if not isdir(SRC_CACHE):
        os.makedirs(SRC_CACHE)

    fn = meta['fn']
    md5 = meta.get('md5')
    path = join(SRC_CACHE, fn)
    if not isfile(path):
        download(meta['url'], path, md5)

    if md5 and not md5_file(path) == md5:
        raise Exception("MD5 mismatch: %r" % meta)
    return path


def unpack(meta):
    src_path = download_to_cache(meta)

    os.makedirs(WORK_DIR)
    if src_path.endswith(('.tar.gz', '.tar.bz2', '.tgz', '.tar.xz', '.tar')):
        tar_xf(src_path, WORK_DIR)
    elif src_path.endswith('.zip'):
        unzip(src_path, WORK_DIR)
    else:
        raise Exception("not a vaild source")


def git_source(meta):
    if not isdir(GIT_CACHE):
        os.makedirs(GIT_CACHE)

    git_url = meta['git_url']
    git_dn = git_url.split(':')[-1].replace('/', '_')
    cache_repo = cache_repo_arg = join(GIT_CACHE, git_dn)
    if sys.platform == 'win32':
        cache_repo_arg = cache_repo_arg.replace('\\', '/')
        if os.getenv('USERNAME') == 'builder':
            cache_repo_arg = '/cygdrive/c/' + cache_repo_arg[3:]

    # update (or craete) the cache repo
    if isdir(cache_repo):
        check_call(['git', 'fetch'], cwd=cache_repo)
    else:
        check_call(['git', 'clone', '--mirror', git_url, cache_repo_arg])
        assert isdir(cache_repo)

    # now clone into the work directory
    checkout = meta.get('git_tag') or meta.get('git_branch') or 'master'
    print 'checkout: %r' % checkout

    check_call(['git', 'clone', cache_repo_arg, WORK_DIR])
    check_call(['git', 'checkout', checkout], cwd=WORK_DIR)

    if meta.get('git_submodules'):
        check_call(['git', 'submodule', 'init'], cwd=WORK_DIR)
        if sys.platform == 'win32':
            from replace import replace
            replace([('https://github.com/', 'git@github.com:')],
                    join(WORK_DIR, '.git', 'config'), assert_change=False)
        check_call(['git', 'submodule', 'update'], cwd=WORK_DIR)

    git_info()
    return WORK_DIR


def git_info(fo=sys.stdout):
    assert isdir(WORK_DIR)
    for cmd, check_error in [
                ('git log -n1', True),
                ('git describe --tags --dirty', False),
                ('git status', True)]:
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE, cwd=WORK_DIR)
        stdout, stderr = p.communicate()
        if check_error and stderr and stderr.strip():
            raise Exception("git error: %s" % stderr)
        fo.write('==> %s <==\n' % cmd)
        fo.write(stdout + '\n')


def apply_patch(src_dir, path):
    print 'Applying patch: %r' % path
    assert isfile(path), path
    patch = r'C:\cygwin\bin\patch' if sys.platform == 'win32' else 'patch'
    check_call([patch, '-p0', '-i', path], cwd=src_dir)


def provide(recipe_dir, meta, patch=True):
    """
    given a recipe_dir:
      - download (if necessary)
      - unpack
      - apply patches (if any)
    """
    rm_rf(WORK_DIR)
    if 'fn' in meta:
        unpack(meta)
    elif 'git_url' in meta:
        git_source(meta)
    else: # no source
        os.makedirs(WORK_DIR)

    if patch:
        src_dir = get_dir()
        for patch in meta.get('patches', []):
            apply_patch(src_dir, join(recipe_dir, patch))


if __name__ == '__main__':
    print provide('.', dict(
        url = 'http://pypi.python.org/packages/source/b/bitarray/bitarray-0.8.0.tar.gz',
        git_url = 'git@github.com:ilanschnell/bitarray.git',
        git_tag = '0.5.2',
    ))
