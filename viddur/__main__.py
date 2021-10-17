#! /usr/bin/python3.9

"""
Mahyar@Mahyar24.com, Fri 11 Jun 2021.
"""


import asyncio
import sys

from .source import check_ffprobe, main


def entry_point():
    assert check_ffprobe(), '"ffprobe" is not found.'
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting ...")
        sys.exit(1)
    else:
        sys.exit(exit_code)


if __name__ == "__main__":
    entry_point()
