import os
from os.path import dirname, exists, isdir, join
import sys
import shutil
import subprocess
from json import load

from conda.base.context import context
from conda.compat import itervalues

PY_TMPL = """\
if __name__ == '__main__':
    import sys
    import %(module)s

    sys.exit(%(module)s.%(func)s())
"""


def get_noarch_cls(noarch_type):
    return NOARCH_CLASSES.get(str(noarch_type).lower(), NoArch) if noarch_type else None


def link_package(src, dst):
    try:
        os.link(src, dst)
        # on Windows os.link raises AttributeError
    except (OSError, AttributeError):
        shutil.copy2(src, dst)


def unlink_package(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def get_python_version_for_prefix(prefix):
    from conda.install import linked_data
    record = next((record for record in itervalues(linked_data(prefix)) if
                   record.name == 'python'), None)
    if record is not None:
        return record.version[:3]
    raise RuntimeError(
        "No python version found in %s. Python required to install noarch package" % prefix
    )


def get_site_packages_dir(prefix):
    if sys.platform == 'win32' or sys.platform == 'win64':
        return join(prefix, 'Lib')
    else:
        return join(prefix, 'lib/python%s' % get_python_version_for_prefix(prefix))


def get_bin_dir(prefix):
    if sys.platform == 'win32' or sys.platform == 'win64':
        return join(prefix, 'Scripts')
    else:
        return join(prefix, 'bin')


def link_files(prefix, src_root, dst_root, files, src_dir):
    dst_files = []
    for f in files:
        src = join(src_dir, src_root, f)
        dst = join(prefix, dst_root, f)
        dst_dir = dirname(dst)
        dst_files.append(dst)
        if not isdir(dst_dir):
            os.makedirs(dst_dir)
        if exists(dst):
            unlink_package(dst)

        link_package(src, dst)
    return dst_files


def compile_missing_pyc(prefix, files, cwd):
    compile_files = []
    for fn in files:
        python_major_version = get_python_version_for_prefix(prefix)[0]
        cache_prefix = ("__pycache__" + os.sep) if python_major_version == '3' else ""
        pyc_name = os.path.dirname(fn) + cache_prefix + os.path.basename(fn) + 'c'
        if fn.endswith(".py") and pyc_name not in files:
            compile_files.append(fn)

    if compile_files:
        print('compiling .pyc files...')
        for f in compile_files:
            subprocess.call(["python", '-Wi', '-m', 'py_compile', f], cwd=cwd)


def create_entry_points(src_dir, bin_dir, prefix):
    entry_points_dst = []
    from conda.install import linked
    if sys.platform == 'win32':
        python_path = join(prefix, "python.exe")
    else:
        python_path = join(prefix, "bin/python")
    get_module = lambda point: point[point.find("= ") + 1:point.find(":")].strip()
    get_func = lambda point: point[point.find(":") + 1:]
    get_cmd = lambda point: point[:point.find("= ")].strip()
    with open(join(src_dir, "info/noarch.json"), "r") as noarch_file:
        entry_points = load(noarch_file)["entry_points"]

    for entry_point in entry_points:
        path = join(bin_dir, get_cmd(entry_point))
        pyscript = PY_TMPL % {'module': get_module(entry_point), 'func': get_func(entry_point)}

        if sys.platform == 'win32':
            with open(path + '-script.py', 'w') as fo:
                packages = linked(prefix)
                packages_names = (pkg.split('-')[0] for pkg in packages)
                if 'debug' in packages_names:
                    fo.write('#!python_d\n')
                fo.write(pyscript)
            link_package(join(dirname(__file__), 'cli-%d.exe' % context.bits), path + '.exe')
            entry_points_dst.append(path + '-script.py')
            entry_points_dst.append(path + '.exe')
        else:
            with open(path, 'w') as fo:
                fo.write('#!%s\n' % python_path)
                fo.write(pyscript)
            os.chmod(path, int('755', 8))
            entry_points_dst.append(path)
    return entry_points_dst


def remove_pycache(package_dir):
    track_path = package_dir
    for doc in os.listdir(package_dir):
        doc_path = join(track_path, doc)
        if doc == '__pycache__':
            shutil.rmtree(doc_path)
        elif isdir(doc_path):
            remove_pycache(doc_path)


def remove_pyc(package_dir):
    track_path = package_dir
    for doc in os.listdir(package_dir):
        doc_path = join(track_path, doc)
        if doc.endswith("pyc"):
            os.remove(doc_path)
        elif isdir(doc_path):
            remove_pyc(doc_path)


class NoArch(object):

    def link(self, prefix, src_dir, dist):
        pass

    def unlink(self, prefix, dist):
        pass


class NoArchPython(NoArch):

    def link(self, prefix, src_dir, dist):
        with open(join(src_dir, "info/files")) as f:
            files = f.read()
        files = files.split("\n")[:-1]

        site_package_files = []
        bin_files = []
        for f in files:
            if f.startswith("site-packages"):
                site_package_files.append(f)
            else:
                if f.startswith("python-scripts"):
                    bin_files.append(f.replace("python-scripts/", ""))

        site_packages_dir = get_site_packages_dir(prefix)
        bin_dir = get_bin_dir(prefix)
        linked_files = link_files(prefix, '', site_packages_dir, site_package_files, src_dir)
        linked_files.extend(link_files(prefix, 'python-scripts', bin_dir, bin_files, src_dir))
        compile_missing_pyc(
            prefix, linked_files, join(prefix, site_packages_dir, 'site-packages')
        )

        linked_files.extend(create_entry_points(src_dir, bin_dir, prefix))

        from conda.install import dist2filename
        alt_files_path = join(prefix, 'conda-meta', dist2filename(dist, '.files'))
        with open(alt_files_path, "w") as alt_files:
            for linked_file in linked_files:
                alt_files.write("%s\n" % linked_file[len(prefix)+1:])

    def unlink(self, prefix, dist):
        package = dist[dist.find("::")+2:dist.find("-")]
        package_dir = os.path.join(get_site_packages_dir(prefix), "site-packages", package)

        python_major_version = get_python_version_for_prefix(prefix)[0]
        if python_major_version == "3":
            remove_pycache(package_dir)
        else:
            remove_pyc(package_dir)


NOARCH_CLASSES = {
    'python': NoArchPython,
    True: NoArch,
}
