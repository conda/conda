from tempfile import gettempdir
from datetime import timedelta
import os

from flufl.lock import Lock

# From the docs:
# Locks have a lifetime, which is the maximum length of time the process expects
# to retain the lock. It is important to pick a good number here because other
# processes will not break an existing lock until the expected lifetime has
# expired. Too long and other processes will hang; too short and you’ll end up
# trampling on existing process locks – and possibly corrupting data. In a
# distributed (NFS) environment, you also need to make sure that your clocks are
# properly synchronized.
#
# TODO find out what a good lifetime is
LIFETIME = 30

def execute(args, parser):
    lock = Lock(os.path.join(gettempdir(), "conda", "locks", args.lockid))
    lock.lifetime = timedelta(seconds=LIFETIME)
    # Set PID to the parent process, in order to allow lock and unlock to be
    # called as separate commands.
    lock._set_claimfile(os.getppid())
    if args.lock:
        lock.lock()
    elif args.unlock:
        lock.unlock()
