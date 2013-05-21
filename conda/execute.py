from pprint import pprint
from collections import defaultdict

#from install import make_available, link, unlink
#from remote import fetch_file
#from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar



def execute(plan):
    actions = defaultdict(list)
    prefix = None

    for action in plan:
        a0, a1 = action
        if a0 == '#':
            continue
        elif a0 == 'PREFIX':
            prefix = a1
        elif a0 in ('FETCH', 'EXTRACT', 'UNLINK', 'LINK'):
            actions[a0].append(a1)
        else:
            raise

    if prefix is None:
        raise

    print prefix
    pprint(dict(actions))


if __name__ == '__main__':
    from plan import _test_plan
    execute(_test_plan())
