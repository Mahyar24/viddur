#! /usr/bin/python3.9

"""
Run this code for see the summed duration of videos.
Compatible with python3.9+. No third-party library is required, implemented in pure python.
Make sure that you have required permissions and "ffprobe" is already installed.
-> https://ffmpeg.org/ffprobe.html
If Some file has a length of zero, this program act with it as a failure.
Consider using "uvloop" and increase the semaphore number to make the program runs faster.
Mahyar@Mahyar24.com, Fri 11 Jun 2021.
"""

import argparse
import asyncio
import mimetypes
import multiprocessing
import os
import shutil
import textwrap
import time
from typing import Iterator, Literal, Union

try:  # If there is uvloop available, use it as event loop.
    import uvloop
except ImportError:
    pass
else:
    uvloop.install()


__all__ = ["main", "check_ffprobe"]

PLACEHOLDER = " ..."  # For pretty printing.
FILES_DUR: dict[str, float] = {}
SEM_NUM = (
    multiprocessing.cpu_count() * 2
)  # Semaphore number for limiting simultaneously open files.
COMMAND = (
    'ffprobe -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{}"'
)
# This Command is all this program based on. "ffprobe" extract the metadata of the file.


def default_terminal_width() -> int:
    """
    Checking the terminal width for shortening filenames.
    """
    try:
        width = os.get_terminal_size()[0]
    except OSError:  # In case of any errors we should have a default.
        width = 80

    return width


def check_ffprobe() -> bool:
    """
    This function check if "ffprobe" is installed or not. shutil.which is cross platform solution.
    """
    if shutil.which("ffprobe") is None:
        return False
    return True


def pretty_print(
    file_name: str, detail: str, args: argparse.Namespace
) -> None:  # One Alternative is to use Rich; but i want to keep it simple and independent.
    """
    Shortening and printing output based on terminal width.
    """
    if args.simple_output:
        print(f"{file_name}: {detail}")
    else:
        shorted_file_name = textwrap.shorten(
            file_name,
            width=max(args.width // 2, len(PLACEHOLDER)),
            placeholder=PLACEHOLDER,
        )
        print(f"{f'{shorted_file_name!r}:':<{max(args.width // 4, 20)}} {detail}")


def format_time(seconds: float, args: argparse.Namespace) -> str:
    """
    Format the time based on cli args. available formats are:
    default, Seconds, Minutes, Hours, Days.
    """
    if args.format is None or args.format == "default":
        res = ""
        days, remainder = divmod(seconds, 86_400)  # 24 * 60 * 60 = 86,400
        if days > 0:
            res = f"{int(days)} day, "
        return res + time.strftime("%H:%M:%S", time.gmtime(remainder))
    if args.format == "s":
        return f"{seconds:,.3f}s"
    if args.format == "m":
        return f"{seconds/60:,.3f}m"
    if args.format == "h":
        return f"{seconds/3_600:,.3f}h"  # 60 * 60 = 3,600
    # d: days for sure because parser check the arg!
    return f"{seconds/86_400:,.3f}d"  # 24 * 60 * 60 = 86,400


def checking_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    """
    if Reversed or Sorted argument was passed without Verbose arg activated, throw an error.
    """
    args = parser.parse_args()
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
    parser = argparse.ArgumentParser(
        epilog=textwrap.dedent(
            """
            Written by: Mahyar Mahdavi <Mahyar@Mahyar24.com>.
            Source Code: https://github.com/mahyar24/viddur
            Reporting Bugs and PRs are welcomed. :)
            """
        )
    )
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
        help="Program doesn't suggest mime types and take all files as videos. "
        "(You should be aware of that 'ffprobe' might recognize weird files duration too)",
        action="store_true",
    )

    parser.add_argument(
        "-f",
        "--format",
        help="Format the duration of the file in [S]econds/[M]inutes/[H]ours/[D]ays or [default]",
        type=lambda x: x.lower()[0] if x.lower() != "default" else "default",
        choices=["default", "s", "m", "h", "d"],
    )

    parser.add_argument(
        "-r",
        "--recursive",
        help="Show duration of videos in directories and their contents recursively",
        action="store_true",
    )

    parser.add_argument(
        "--sem",
        "--semaphore",
        help="Limiting number of parallel open files.",
        type=int,
        default=SEM_NUM,
    )

    parser.add_argument(
        "-w",
        "--width",
        help="Width of your terminal size. (for shortening filenames)",
        type=int,
        default=default_terminal_width(),
    )

    parser.add_argument(
        "--simple-output",
        help="Deactivate pretty printing and shortening of filenames.",
        action="store_true",
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
        "--reverse",
        help="In verbose mode this option make the output sorted in descending order",
        action="store_true",
    )

    return checking_args(parser)


async def find_duration(file: str) -> Union[float, Literal[False]]:
    """
    Get a filename and extract the duration of it. it will return False for failure.
    """
    process = await asyncio.create_subprocess_shell(
        COMMAND.format(file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await process.communicate()

    if (
        not process.returncode and stdout != b"N/A\n" and (res := float(stdout))
    ):  # In some cases ffprobe return a successful 0 code but the duration is N/A.
        # furthermore if duration of file is "0" then there is something wrong!
        return res
    return False


async def handle(
    file: str, sem: asyncio.locks.Semaphore, args: argparse.Namespace
) -> int:
    """
    Get a filename and based on the result of processing it, print of store and return status code.
    """

    mime_guess = mimetypes.guess_type(file)[0]
    if args.all or (mime_guess is not None and mime_guess.split("/")[0] == "video"):
        async with sem:  # With cautious of not opening too much file at the same time.
            result = await find_duration(file)
        if result:
            duration = result
            FILES_DUR[file] = duration
            if args.verbose:
                if not (args.sort or args.reverse):
                    pretty_print(file, format_time(duration, args), args)
            return 0
        if not args.quiet:
            if not (args.sort or args.reverse):
                pretty_print(file, "cannot get examined.", args)
            else:
                FILES_DUR[file] = 0.0
        return 1
    if args.verbose:
        if not (args.sort or args.reverse):
            pretty_print(file, "is not recognized as a media.", args)
        else:
            FILES_DUR[file] = 0.0  # same as `FILES_DUR[file] = False`
    return 0


def sorted_msgs(args: argparse.Namespace) -> None:
    """
    Printing Sorted durations.
    """
    # noinspection PyTypeChecker
    sorted_dict = dict(
        sorted(FILES_DUR.items(), key=lambda item: item[1], reverse=args.reverse)
    )
    for key, value in sorted_dict.items():
        if value:
            pretty_print(key, format_time(value, args), args)
        else:  # if value == 0.0, this is a failure.
            pretty_print(key, "cannot get examined.", args)


def cleanup_inputs(args: argparse.Namespace) -> Union[list[str], Iterator[str]]:
    """
    Delivering list of all files based on our parsed arguments.
    """
    if args.recursive:  # Asserting for bad use of --recursive option.
        if len(args.path_file) != 1 or not os.path.isdir(args.path_file[0]):
            raise NotADirectoryError(
                "with --recursive option, you should specify only one directory."
            )

    if len(args.path_file) == 1 and os.path.isfile(
        args.path_file[0]
    ):  # Single filename.
        files = args.path_file
    elif (
        len(args.path_file) > 1
    ):  # It must be a list of files (e.g. 1.mkv 2.mp4) or a wildcard (e.g. *.avi)
        if all(
            os.path.isfile(name) for name in args.path_file
        ):  # Check if all of inputs are files.
            files = args.path_file
        else:
            raise FileExistsError("With multiple inputs you must provide only files.")
    elif os.path.isdir((directory := args.path_file[0])):
        if args.recursive:
            files = (
                os.path.join(os.path.relpath(path), file)
                for path, _, files_list in os.walk(top=directory)
                for file in files_list
            )
        else:
            os.chdir(directory)
            files = (file for file in os.listdir() if os.path.isfile(file))
    else:  # in case of a single invalid argument (e.g. viddur fake) we should fail.
        raise NotADirectoryError(f"{directory!r} is not a valid directory or filename.")

    return files


async def main() -> int:
    """
    main function. This program is CLI based and you shouldn't run it as a package.
    """
    args = parsing_args()
    files = cleanup_inputs(args)
    sem = asyncio.Semaphore(args.sem)
    tasks = [asyncio.create_task(handle(file, sem, args)) for file in files]
    results = await asyncio.gather(*tasks)

    if tasks:
        if args.sort or args.reverse:
            sorted_msgs(args)
        exit_code = int(
            any(results)
        )  # Check to see if any of the checked file is failed; for the return code.
    else:  # bad arguments -> returning failure return code.
        exit_code = 1

    prefix = "" if args.quiet else "\nTotal Time is: "
    print(prefix + format_time(sum(FILES_DUR.values()), args))

    return exit_code
