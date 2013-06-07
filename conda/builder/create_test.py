import inspect
import shutil
from os.path import dirname, join

from config import croot
from metadata import parse, sel_pat, ns_cfg


TEST_TARS_DIR = join(croot, 'test-tars')


def parse_meta(path):
    data = open(path).read()
    d = parse(data)
    return d['test']


def write_if(fo, line):
    line = line.rstrip()
    m = sel_pat.match(line)
    if m is None:
        fo.write('if True:\n')
        return line
    else:
        fo.write('if applies(%r):\n' % m.group(2))
        return m.group(1)


def create_test_files(dir_path, m):
    """
    Create the test files for pkg in the directory given.  The resulting
    test files are configuration (i.e. platform, architecture, Python and
    numpy version, CE/Pro) independent.
    Return False, if the package has no tests (for any configuration), and
    True if it has.
    """
    meta = parse_meta(join(m.path, 'meta.yaml'))
    has_tests = False
    #print meta

    for fn in meta['files']:
        shutil.copy(join(m.path, fn), dir_path)

    with open(join(dir_path, 'run_test.py'), 'w') as fo:
        fo.write("# tests for %s (this is a gernerated file)\n" %
                 m.dist_name())
        fo.write("print('===== testing package: %s =====')\n" % m.dist_name())
        with open(join(dirname(__file__), 'header_test.py')) as fi:
            fo.write(fi.read() + '\n')
        fo.write(inspect.getsource(ns_cfg) + '\n')

        for line in meta['commands']:
            cmd = write_if(fo, line)
            fo.write('    print("command: %s")\n' % cmd)
            fo.write('    check_call(cmd_args(%r))\n\n' % cmd)
            has_tests = True

        for line in meta['imports']:
            line = write_if(fo, line)
            fo.write('    print("import: %s")\n' % line)
            name, extra = split_import_line(line)
            fo.write('    import %s\n' % name)
            has_tests = True
            fo.write('\n')

        try:
            with open(join(m.path, 'run_test.py')) as fi:
                fo.write("# --- run_test.py (begin) ---\n")
                fo.write(fi.read())
                fo.write("# --- run_test.py (end) ---\n")
            has_tests = True
        except IOError:
            fo.write("# no run_test.py exists for this package\n")
        fo.write("\nprint('===== %s OK =====')\n" % m.dist_name())

    return has_tests
