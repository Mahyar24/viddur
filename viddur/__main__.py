#! /usr/bin/python3.9

"""
Mahyar@Mahyar24.com, Fri 11 Jun 2021.
"""


import asyncio
import sys

from source import check_ffprobe, main

if __name__ == "__main__":
    assert check_ffprobe(), '"ffprobe" is not found.'
    try:
        EXIT_CODE = asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting ...")
        sys.exit(1)
    else:
        # noinspection PyUnboundLocalVariable
        sys.exit(EXIT_CODE)
