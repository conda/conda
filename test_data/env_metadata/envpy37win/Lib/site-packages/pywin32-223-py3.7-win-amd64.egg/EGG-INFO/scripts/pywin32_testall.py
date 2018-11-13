"""A test runner for pywin32"""
import sys
import os
import distutils.sysconfig
import win32api

# locate the dirs based on where this script is - it may be either in the
# source tree, or in an installed Python 'Scripts' tree.
this_dir = os.path.dirname(__file__)
site_packages = distutils.sysconfig.get_python_lib(plat_specific=1)

if hasattr(os, 'popen3'):
    def run_test(script, cmdline_rest=""):
        dirname, scriptname = os.path.split(script)
        # some tests prefer to be run from their directory.
        cwd = os.getcwd()
        os.chdir(dirname)
        try:
            executable = win32api.GetShortPathName(sys.executable)
            cmd = '%s "%s" %s' % (sys.executable, scriptname, cmdline_rest)
            print(script)
            stdin, stdout, stderr = os.popen3(cmd)
            stdin.close()
            while 1:
                char = stderr.read(1)
                if not char:
                    break
                sys.stdout.write(char)
            for line in stdout.readlines():
                print(line)
            stdout.close()
            result = stderr.close()
            if result is not None:
                print("****** %s failed: %s" % (script, result))
        finally:
            os.chdir(cwd)
else:
    # a subprocess version - but we prefer the popen one if we can as we can
    # see test results as they are run (whereas this one waits until the test
    # is finished...)
    import subprocess
    def run_test(script, cmdline_rest=""):
        dirname, scriptname = os.path.split(script)
        # some tests prefer to be run from their directory.
        cmd = [sys.executable, "-u", scriptname] + cmdline_rest.split()
        print(script)
        popen = subprocess.Popen(cmd, shell=True, cwd=dirname,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        data = popen.communicate()[0]
        sys.stdout.buffer.write(data)
        if popen.returncode:
            print("****** %s failed: %s" % (script, popen.returncode))


def find_and_run(possible_locations, script, cmdline_rest=""):
    for maybe in possible_locations:
        if os.path.isfile(os.path.join(maybe, script)):
            run_test(os.path.abspath(os.path.join(maybe, script)), cmdline_rest)
            break
    else:
        raise RuntimeError("Failed to locate the test script '%s' in one of %s"
                           % (script, possible_locations))

if __name__=='__main__':
    # win32
    maybes = [os.path.join(this_dir, "win32", "test"),
              os.path.join(site_packages, "win32", "test"),
             ]
    find_and_run(maybes, 'testall.py')

    # win32com
    maybes = [os.path.join(this_dir, "com", "win32com", "test"),
              os.path.join(site_packages, "win32com", "test"),
             ]
    find_and_run(maybes, 'testall.py', "2")

    # adodbapi
    maybes = [os.path.join(this_dir, "adodbapi", "tests"),
              os.path.join(site_packages, "adodbapi", "tests"),
             ]
    find_and_run(maybes, 'adodbapitest.py')
    # This script has a hard-coded sql server name in it, (and markh typically
    # doesn't have a different server to test on) so don't bother trying to
    # run it...
    # find_and_run(maybes, 'test_adodbapi_dbapi20.py')

    if sys.version_info > (3,):
        print("** The tests have some issues on py3k - not all failures are a problem...")