import os
import mimetypes
import time
import asyncio
import argparse
import sys


TOTAL = 0
COMMAND = 'ffprobe -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{}"'


def parsing_options():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()

    parser.add_argument(
        "path_file",
        nargs="*",
        default=[os.getcwd()],
        help="Select desired directory or files, default is $PWD.",
    )
    parser.add_argument(
        "-a",
        "--all",
        help="Program doesn't suggest mime types and take all files as videos.",
        action="store_true",
    )
    group.add_argument(
        "-v",
        "--verbose",
        help="show all of the video's duration too.",
        action="store_true",
    )
    group.add_argument(
        "-q",
        "--quiet",
        help="return only the duration without any further explanation",
        action="store_true",
    )

    return parser.parse_args()


def format_time(seconds):
    gm_time = time.gmtime(seconds)
    res = ""
    if (day := gm_time.tm_mday) > 1:
        res = f"{day - 1} day, "
    return res + time.strftime("%H:%M:%S", gm_time)


async def calc(file):
    global TOTAL

    mime_guess = mimetypes.guess_type(file)[0]
    if ARGS.all or (mime_guess is not None and mime_guess.split("/")[0] == "video"):
        process = await asyncio.subprocess.create_subprocess_shell(
            COMMAND.format(file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await process.communicate()

        if not process.returncode:
            duration = float(stdout)
            TOTAL += float(stdout)

            if ARGS.verbose:
                print(f'"{file}": {format_time(duration)}')
        else:
            if not ARGS.quiet:
                print(f'"{file}" cannot get examined.')
    else:
        if ARGS.verbose:
            print(f'"{file}" is not recognized as a media.')
        return 1

    return process.returncode


async def main():
    if len(ARGS.path_file) > 1 or os.path.isfile(ARGS.path_file[0]):
        files = ARGS.path_file
    else:
        files = os.listdir(ARGS.path_file[0])

    tasks = [asyncio.create_task(calc(file)) for file in files if os.path.isfile(file)]
    results = await asyncio.gather(*tasks)
    if tasks:
        return any(results)
    return 1


if __name__ == "__main__":
    ARGS = parsing_options()
    exit_code = asyncio.run(main())
    prefix = "" if ARGS.quiet else "Total Time is: "
    print(prefix + format_time(TOTAL))
    sys.exit(exit_code)
