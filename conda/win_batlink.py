"""
Generate batch scripts to allow conda to update Python in the root
environment in Windows.  conda cannot do this because it itself runs in
Python, and Windows will not allow writing to a dll that is open.

The scripts should remain as small as possible. Only those things that conda
itself cannot do should be in them. The rest should be done by conda.

The way this works is that when conda comes to an action that it cannot
perform (such as linking Python in the root environment), it serializes the
rest of the actions it intends to perform, serializes the action that it
cannot perform into a batch script (that's what's done here in this module),
calls this script, and exits (see conda.plan.execute_plan()). This script then
performs the action conda could not perform and then calls conda to continue
where it left off.

Implementation wise, the conda searlization is just a text dump of the
remainder of the plan in %PREFIX%\remainder.plan. The plan is already in a
nice text format (see tests/simple.plan for an example), so little work needs
to be done serialization-wise. The action serialization is just a custom batch
file that does the linking of everything in the package list of pairs of files
that should be linked, written to %PREFIX%\batlink.bat (note, we can assume
that we have write permissions to %PREFIX% because otherwise we wouldn't be
able to install in the root environment anyway (this issue only comes up when
installing into the root environment)). conda calls this script and
exits. This script reads the action file, links the files listed therein, and
calls conda ..continue (and then exits). conda ..continue causes conda to pick
up where it left off from the remainder.plan file.

Notes:

- `mklink /H` creates a hardlink on Windows NT 6.0 and later (i.e., Windows
Vista or later)
- On older systems, like Windows XP, `fsutil.exe hardlink create` creates
hard links.
- In either case, the order of the arguments is backwards: dest source

"""

import os.path
from os.path import join, isdir
import platform

BAT_HEADER  = """\
{deletes}
{links}

conda ..continue {verboseflag}
"""

WINXP_LINK = "fsutil.exe hardlink create {dest} {source}"

WINVISTA_LINK = "mklink /H {dest} {source}"

DELETE = "del {dest}"

def make_bat(files, prefix, dist_dir, verbose=False, link=True):
    verboseflag = "-v" if verbose else ""
    deletes = []
    links = []
    LINK = WINXP_LINK if platform.win32_ver()[0] == 'XP' else WINVISTA_LINK
    for file in files:
        source = join(dist_dir, file)
        fdn, fbn = os.path.split(file)
        dst_dir = join(prefix, fdn)
        if not isdir(dst_dir):
            os.makedirs(dst_dir)
        dest = join(dst_dir, fbn)
        deletes.append(DELETE.format(dest=dest))
        if link:
            links.append(LINK.format(source=source, dest=dest))

    batchfile = BAT_HEADER.format(deletes='\n'.join(deletes),
        links='\n'.join(links), verboseflag=verboseflag)

    filepath = join(prefix, 'batlink.bat')
    with open(filepath, 'w') as f:
        f.write(batchfile)

    return filepath
