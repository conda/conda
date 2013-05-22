import install
from config import PKGS_DIR
from naming import name_dist
from remote import fetch_file
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar



def fetch(index, dist, progress):
    fn = dist + '.tar.bz2'
    info = index[fn]
    fetch_file(info['channel'], fn, md5=info['md5'], size=info['size'],
               progress=progress)

def cmds_from_plan(plan):
    res = []
    for line in plan:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        res.append(line.split(None, 1))
    return res

def execute(plan, index=None, enable_progress=True):
    if enable_progress:
        fetch_progress = ProgressBar(
            widgets=['', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
                     FileTransferSpeed()])
        progress = ProgressBar(
            widgets=['', ' ', Bar(), ' ', Percentage()])
    else:
        fetch_progress = None
        progress = None

    progress_cmds = set(['EXTRACT', 'REMOVE', 'LINK', 'UNLINK', 'SLEEP'])
    prefix = i = None
    for cmd, arg in cmds_from_plan(plan):
        if enable_progress and cmd in progress_cmds:
            i += 1
            progress.widgets[0] = '[%-20s]' % name_dist(arg)
            progress.update(i)

        if cmd == 'PREFIX':
            prefix = arg
        elif cmd == 'PRINT':
            print arg
        elif cmd == 'FETCH':
            fetch(index or {}, arg, fetch_progress)
        elif cmd == 'PROGRESS' and enable_progress:
            progress.maxval = int(arg)
            progress.start()
            i = 0
        elif cmd == 'EXTRACT':
            install.extract(PKGS_DIR, arg)
        elif cmd == 'REMOVE':
            install.remove(PKGS_DIR, arg)
        elif cmd == 'LINK':
            install.link(PKGS_DIR, arg, prefix)
        elif cmd == 'UNLINK':
            install.unlink(arg, prefix)
        elif cmd == 'SLEEP':
            import time
            time.sleep(float(arg.split('-')[1]))
        else:
            raise Exception("Did not expect command: %r" % cmd)

        if enable_progress and cmd in progress_cmds and progress.maxval == i:
            progress.widgets[0] = '[      COMPLETE      ]'
            progress.finish()


if __name__ == '__main__':
    plan = """
PREFIX /Users/ilan/python/envs/test
PRINT Sleeping ...
PROGRESS 4
SLEEP numpy-0.6
SLEEP bitarray-0.4
SLEEP pycosat-0.2
SLEEP python-0.7
"""
    execute(plan.splitlines())
