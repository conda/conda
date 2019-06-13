from tempfile import gettempdir
import os

from flufl.lock import Lock

def execute(args, parser):
    lock = Lock(os.path.join(gettempdir(), "conda", "locks", args.lockid))
    # Set PID to the parent process, in order to allow lock and unlock to be
    # called as separate commands.
    lock._set_claimfile(os.getppid())
    if args.lock:
        lock.lock()
    elif args.unlock:
        lock.unlock()
