#! /usr/bin/python3.9

# Run this code for see the summed duration of videos.
# Compatible with python3.9+. No third-party library is required, implemented in pure python.
# Make sure that you have required permissions and "ffprobe" is already installed.
# Mahyar@Mahyar24.com, Fri 11 Jun 2021.


import argparse
import asyncio
import mimetypes
import os
import sys
import textwrap
import time

TOTAL = 0.0  # Global variables are async safe.
PLACEHOLDER = " ..."  # For pretty printing.
FILES_DUR: dict[str, float] = {}
COMMAND = (
    'ffprobe -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{}"'
)
# This Command is all this program based on. "ffprobe" extract the metadata of the file.


def pretty_print(
    file_name: str, detail: str
) -> None:  # One Alternative is to use Rich; but i want to keep it simple and independent.
    """
    Shortening and printing output based on terminal width.
    """
    width = os.get_terminal_size()[0]
    shorted_file_name = textwrap.shorten(
        file_name, width=max(width // 2, len(PLACEHOLDER)), placeholder=PLACEHOLDER
    )
    print(f"{f'{shorted_file_name!r}:':<{max(width // 4, 20)}} {detail}")


def format_time(seconds: float) -> str:
    """
    Format the time based of cli args. available formats are: default, Seconds, Minutes, Hours, Days.
    """
    if ARGS.format is None or ARGS.format == "default":
        gm_time = time.gmtime(seconds)
        res = ""
        if (day := gm_time.tm_mday) > 1:
            res = f"{day - 1} day, "
        return res + time.strftime("%H:%M:%S", gm_time)
    elif ARGS.format == "s":
        return f"{seconds:.3f}s"
    elif ARGS.format == "m":
        return f"{seconds/60:.3f}m"
    elif ARGS.format == "h":
        return f"{seconds/(60 * 60):.3f}h"
    else:  # d: days for sure because parser check the arg!
        return f"{seconds/(24 * 60 * 60):.3f}d"


def checking_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> argparse.Namespace:
    """
    if Reversed or Sorted argument was passed without Verbose arg activated, throw an error.
    """
    if not args.verbose:
        if args.sort or args.reverse:
            parser.error(
                "You should use -v (--verbose) argument first for getting the output sorted"
            )
    return args


def parsing_args() -> argparse.Namespace:
    """
    Parsing the passed arguments, read help (-h, --help) for further information.
    """
    parser = argparse.ArgumentParser()
    group_vq = parser.add_mutually_exclusive_group()
    group_sr = parser.add_mutually_exclusive_group()

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

    parser.add_argument(
        "-f",
        "--format",
        help="Format the duration of the file in [S]econds/[M]inutes/[H]ours/[D]ays or [default]",
        type=lambda x: x.lower()[0] if x.lower() != "default" else "default",
        choices=["default", "s", "m", "h", "d"],
    )

    group_vq.add_argument(
        "-v",
        "--verbose",
        help="show all of the video's duration too.",
        action="store_true",
    )
    group_vq.add_argument(
        "-q",
        "--quiet",
        help="return only the duration without any further explanation",
        action="store_true",
    )

    group_sr.add_argument(
        "-s",
        "--sort",
        help="In verbose mode this option make the output sorted in ascending order",
        action="store_true",
    )

    group_sr.add_argument(
        "-r",
        "--reverse",
        help="In verbose mode this option make the output sorted in descending order",
        action="store_true",
    )

    return checking_args(parser.parse_args(), parser)


async def calc(file: str) -> int:
    """
    Get a filename and extract the duration of it. it will return 0 for successful operation and 1 for failure.
    """
    global TOTAL
    global FILES_DUR

    mime_guess = mimetypes.guess_type(file)[0]
    if ARGS.all or (mime_guess is not None and mime_guess.split("/")[0] == "video"):
        process = await asyncio.subprocess.create_subprocess_shell(
            COMMAND.format(file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await process.communicate()

        if (
            not process.returncode and stdout != b"N/A\n"
        ):  # In some cases ffprobe return a successful 0 code but the duration is N/A.
            duration = float(stdout)
            TOTAL += float(stdout)

            if ARGS.verbose:
                if not (ARGS.sort or ARGS.reverse):
                    pretty_print(file, format_time(duration))
                else:
                    FILES_DUR[file] = duration
            return 0
        else:
            if not ARGS.quiet:
                pretty_print(file, "cannot get examined.")
            return 1
    else:
        if ARGS.verbose:
            if not (ARGS.sort or ARGS.reverse):
                pretty_print(file, "is not recognized as a media.")
            else:
                FILES_DUR[file] = False
        return 0


def sorted_msgs() -> None:
    """
    Printing Sorted durations.
    """
    sorted_dict = {
        k: v
        for k, v in sorted(
            FILES_DUR.items(),
            key=lambda x: x[1],
            reverse=ARGS.reverse,
        )
    }
    for k, v in sorted_dict.items():
        if v:
            pretty_print(k, format_time(v))
        else:
            pretty_print(k, "cannot get examined.")


async def main() -> int:
    if len(ARGS.path_file) > 1 or os.path.isfile(
        ARGS.path_file[0]
    ):  # Check if it's a list of files (e.g. 1.mkv 2.mp4) or a wildcard (e.g. *.avi) or a single filename.
        files = ARGS.path_file
    else:  # it's a directory.
        os.chdir(ARGS.path_file[0])
        files = os.listdir()

    tasks = [
        asyncio.create_task(calc(file)) for file in files if os.path.isfile(file)
    ]  # the if statement is necessary because there's a possibility of existence of a nested directory or passing -
    # two directory names.
    results = await asyncio.gather(*tasks)
    if tasks:
        if ARGS.sort or ARGS.reverse:
            sorted_msgs()
        return any(
            results
        )  # Check to see if any of the checked file is failed; for the return code.
    return 1  # bad arguments -> returning failure return code.


if __name__ == "__main__":
    ARGS = parsing_args()
    exit_code = asyncio.run(main())
    prefix = "" if ARGS.quiet else "\nTotal Time is: "
    print(prefix + format_time(TOTAL))
    sys.exit(exit_code)
