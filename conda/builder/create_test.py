from __future__ import print_function, division, absolute_import

import shutil
from os.path import dirname, join



def create_files(dir_path, m):
    """
    Create the test files for pkg in the directory given.  The resulting
    test files are configuration (i.e. platform, architecture, Python and
    numpy version, CE/Pro) independent.
    Return False, if the package has no tests (for any configuration), and
    True if it has.
    """
    has_tests = False

    for fn in m.get_value('test/files'):
        shutil.copy(join(m.path, fn), dir_path)

    with open(join(dir_path, 'run_test.py'), 'w') as fo:
        fo.write("# tests for %s (this is a generated file)\n" % m.dist())
        fo.write("print('===== testing package: %s =====')\n" % m.dist())
        with open(join(dirname(__file__), 'header_test.py')) as fi:
            fo.write(fi.read() + '\n')

        for cmd in m.get_value('test/commands'):
            # Use two levels of indirection in case cmd contains quotes
            fo.write('print(%r)\n'% ("command: %r" % cmd))
            fo.write('call_args(%r)\n\n' % cmd)
            has_tests = True

        for name in m.get_value('test/imports'):
            fo.write('print("import: %r")\n' % name)
            fo.write('import %s\n' % name)
            fo.write('\n')
            has_tests = True

        try:
            with open(join(m.path, 'run_test.py')) as fi:
                fo.write("# --- run_test.py (begin) ---\n")
                fo.write(fi.read())
                fo.write("# --- run_test.py (end) ---\n")
            has_tests = True
        except IOError:
            fo.write("# no run_test.py exists for this package\n")
        fo.write("\nprint('===== %s OK =====')\n" % m.dist())

    return has_tests
