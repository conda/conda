from tempfile import gettempdir
from datetime import timedelta
import os

from flufl.lock import Lock

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
