# -*- encoding: utf-8 -*-
"""Executable module.

Why does this file exist, and why __main__?
For more info, read:
- https://www.python.org/dev/peps/pep-0338/
- https://docs.python.org/2/using/cmdline.html#cmdoption-m
- https://docs.python.org/3/using/cmdline.html#cmdoption-m
"""
import sys


def main(argv=()):
    """Execute Don't Forget as a module.

    :param argv: List of arguments.
    :return: A return code.

    :type argv: list
    :rtype: int
    """
    print(argv)
    return 0

if __name__ == "__main__":
    sys.exit(main())
