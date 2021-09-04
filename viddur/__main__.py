#! /usr/bin/python3.9

"""
Mahyar@Mahyar24.com, Fri 11 Jun 2021.
"""


import asyncio
import sys

from main import check_ffprobe, main

if __name__ == "__main__":
    assert check_ffprobe(), '"ffprobe" is not found.'
    exit_code = asyncio.run(main())

    sys.exit(exit_code)
