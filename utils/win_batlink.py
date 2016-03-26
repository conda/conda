# UNUSED MODULE
"""
Generate batch scripts to allow conda to update Python in the root
environment in Windows.  conda cannot do this because it itself runs in
Python, and Windows will not allow writing to a dll that is open.

The scripts should remain as small as possible. Only those things that conda
itself cannot do should be in them. The rest should be done by conda.

The way this works is that when conda comes to an action that it cannot
perform (such as linking Python in the root environment), it serializes the
actions that it cannot perform into a batch script (that's what's done here in
this module), performs the rest of the actions that it can perform, calls this
script, and exits (see conda.plan.execute_plan()).

Implementation wise, the action serialization is just a custom batch file that
does the linking/unlinking of everything in the package list, written to
%PREFIX%\batlink.bat (note, we can assume that we have write permissions to
%PREFIX% because otherwise we wouldn't be able to install in the root
environment anyway (this issue only comes up when installing into the root
environment)). conda calls this script and exits.

Notes:

- `mklink /H` creates a hardlink on Windows NT 6.0 and later (i.e., Windows
Vista or later)
- On older systems, like Windows XP, `fsutil.exe hardlink create` creates
hard links.
- In either case, the order of the arguments is backwards: dest source

"""

from os.path import join, abspath, split
from distutils.spawn import find_executable

# Redirect stderr on the mkdirs to ignore errors about directories that
# already exist
BAT_LINK_HEADER = """\

{mkdirs}


{links}

"""

# Hide stderr for this one because it warns about nonempty directories, like
# C:\Anaconda.
BAT_UNLINK_HEADER = """\
{filedeletes}

{dirdeletes}

"""

WINXP_LINK = "fsutil.exe hardlink create {dest} {source}"

WINVISTA_LINK = "mklink /H {dest} {source}"

MAKE_DIR = "mkdir {dst_dir}"

FILE_DELETE = "del /Q {dest}"

DIR_DELETE = "rmdir /Q {dest}"


def make_bat_link(files, prefix, dist_dir):
    links = []
    has_mklink = find_executable('mklink')
    LINK = WINVISTA_LINK if has_mklink else WINXP_LINK
    dirs = set()
    for file in files:
        source = abspath(join(dist_dir, file))
        fdn, fbn = split(file)
        dst_dir = join(prefix, fdn)
        dirs.add(abspath(dst_dir))
        dest = abspath(join(dst_dir, fbn))
        links.append(LINK.format(source=source, dest=dest))

    # mkdir will make intermediate directories, so we do not need to care
    # about the order
    mkdirs = [MAKE_DIR.format(dst_dir=dn) for dn in dirs]

    batchfile = BAT_LINK_HEADER.format(links='\n'.join(links),
                                       mkdirs='\n'.join(mkdirs))

    return batchfile


def make_bat_unlink(files, directories, prefix, dist_dir):
    filedeletes = [FILE_DELETE.format(dest=abspath(file)) for file in files]
    dirdeletes = [DIR_DELETE.format(dest=abspath(dir)) for dir in directories]
    batchfile = BAT_UNLINK_HEADER.format(filedeletes='\n'.join(filedeletes),
                                         dirdeletes='\n'.join(dirdeletes))

    return batchfile


def should_do_win_subprocess(cmd, arg, prefix):
    """
    If the cmd needs to call out to a separate process on Windows (because the
    Windows file lock prevents Python from updating itself).
    """
    return (
        cmd in ('LINK', 'UNLINK') and
        install.on_win and
        abspath(prefix) == abspath(sys.prefix) and
        arg.rsplit('-', 2)[0] in install.win_ignore
    )

def win_subprocess_re_sort(plan, prefix):
    # TODO: Fix the progress numbers
    newplan = []
    winplan = []
    for line in plan:
        cmd_arg = cmds_from_plan([line])
        if cmd_arg:
            [[cmd, arg]] = cmd_arg
        else:
            continue
        if should_do_win_subprocess(cmd, arg, prefix=prefix):
            if cmd == LINK:
                # The one post-link action that we need to worry about
                newplan.append("CREATEMETA %s" % arg)
            winplan.append(line)
        else:
            newplan.append(line)

    return newplan, winplan


def test_win_subprocess(prefix):
    """
    Make sure the windows subprocess stuff will work before we try it.
    """
    import subprocess
    from conda.win_batlink import make_bat_link, make_bat_unlink
    from conda.builder.utils import rm_rf

    try:
        print("Testing if we can install certain packages")
        batfiles = ['ping 1.1.1.1 -n 1 -w 3000 > nul']
        dist_dir = join(config.pkgs_dir, 'battest_pkg', 'battest')

        # First create a file in the prefix.
        print("making file in the prefix")
        prefix_battest = join(prefix, 'battest')
        print("making directories")
        os.makedirs(join(prefix, 'battest'))
        print("making file")
        with open(join(prefix_battest, 'battest1'), 'w') as f:
            f.write('test1')
        print("testing file")
        with open(join(prefix_battest, 'battest1')) as f:
            assert f.read() == 'test1'

        # Now unlink it.
        print("making unlink command")
        batfiles.append(make_bat_unlink([join(prefix_battest, 'battest1')],
        [prefix_battest], prefix, dist_dir))

        # Now create a file in the pkgs dir
        print("making file in pkgs dir")
        print("making directories")
        os.makedirs(join(dist_dir, 'battest'))
        print("making file")
        with open(join(dist_dir, 'battest', 'battest2'), 'w') as f:
            f.write('test2')
        print("testing file")
        with open(join(dist_dir, 'battest', 'battest2')) as f:
            assert f.read() == 'test2'

        # And link it
        print("making link command")
        batfiles.append(make_bat_link([join('battest', 'battest2')],
                                      prefix, dist_dir))

        batfile = '\n'.join(batfiles)

        print("writing batlink_test.bat file")
        with open(join(prefix, 'batlink_test.bat'), 'w') as f:
            f.write(batfile)
        print("running batlink_test.bat file")
        subprocess.check_call([join(prefix, 'batlink_test.bat')])

        print("testing result")
        print("testing if old file does not exist")
        assert not os.path.exists(join(prefix_battest, 'battest1'))
        print("testing if new file does exist")
        assert os.path.exists(join(prefix_battest, 'battest2'))
        print("testing content of installed file")
        with open(join(prefix_battest, 'battest2')) as f:
            assert f.read() == 'test2'
        print("testing content of pkg file")
        with open(join(dist_dir, 'battest', 'battest2')) as f:
            assert f.read() == 'test2'

    finally:
        try:
            print("cleaning up")
            rm_rf(join(prefix, 'battest'))
            rm_rf(join(config.pkgs_dir, 'battest_pkg'))
            rm_rf(join(prefix, 'batlink_test.bat'))
        except Exception as e:
            print(e)


def win_subprocess_write_bat(cmd, arg, prefix, plan):
    assert sys.platform == 'win32'

    import json
    from conda.win_batlink import make_bat_link, make_bat_unlink

    dist_dir = join(config.pkgs_dir, arg)
    info_dir = join(dist_dir, 'info')

    if cmd == LINK:
        files = list(install.yield_lines(join(info_dir, 'files')))

        return make_bat_link(files, prefix, dist_dir)

    elif cmd == UNLINK:
        meta_path = join(prefix, 'conda-meta', arg + '.json')
        with open(meta_path) as fi:
            meta = json.load(fi)

        files = set([])
        directories1 = set([])
        for f in meta['files']:
            dst = abspath(join(prefix, f))
            files.add(dst)
            directories1.add(dirname(dst))
        files.add(meta_path)

        directories = set([])
        for path in directories1:
            while len(path) > len(prefix):
                directories.add(path)
                path = dirname(path)
        directories.add(join(prefix, 'conda-meta'))
        directories.add(prefix)

        directories = sorted(directories, key=len, reverse=True)

        return make_bat_unlink(files, directories, prefix, dist_dir)
    else:
        raise ValueError


def do_win_subprocess(batfile, prefix):
    import subprocess
    with open(join(prefix, 'batlink.bat'), 'w') as f:
        f.write(batfile)
    print("running subprocess")
    subprocess.Popen([join(prefix, 'batlink.bat')])
    # If we ever hit a race condition, maybe we should use atexit
    sys.exit(0)
