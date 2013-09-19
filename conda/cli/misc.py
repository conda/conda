from __future__ import print_function, division, absolute_import

import sys

import conda.config
import conda.plan


def main():
    assert sys.argv[1] in ('..changeps1')

    if sys.argv[1] == '..changeps1':
        print(int(conda.config.changeps1))
        sys.exit(0)


if __name__ == '__main__':
    main()
