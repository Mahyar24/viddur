#! /usr/bin/python3.9

# Run this code for see the summed duration of videos.
# Compatible with python3.9+. No third-party library is required, implemented in pure python.
# Make sure that you have required permissions and "ffprobe" is already installed.
# Mahyar@Mahyar24.com, Fri 11 Jun 2021.


import argparse
import asyncio
import mimetypes
import os
import shutil
import sys
import textwrap
import time

TOTAL = 0.0  # Global variables are async safe.
PLACEHOLDER = " ..."  # For pretty printing.
FILES_DUR: dict[str, float] = {}
SEM_NUM = 25  # Semaphore number for limiting simultaneously open files.
COMMAND = (
    'ffprobe -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{}"'
)
# This Command is all this program based on. "ffprobe" extract the metadata of the file.


def check_ffprobe() -> bool:
    """
    This function check if "ffprobe" is installed or not. shutil.which is cross platform solution.
    """
    if shutil.which("ffprobe") is None:
        return False
    return True


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

    parser.add_argument(
        "-r",
        "--recursive",
        help="Show duration of videos in directories and their contents recursively",
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


async def calc_with_cautious(file: str, sem: asyncio.locks.Semaphore) -> int:
    """
    Calculate length of file with cautious of not opening too much file at the same time.
    """
    async with sem:
        return await calc(file)


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


def cleanup_inputs() -> list[str]:
    """
    Delivering list of all files based on our parsed arguments.
    """
    if len(ARGS.path_file) == 1 and os.path.isfile(
        ARGS.path_file[0]
    ):  # Single filename.
        files = ARGS.path_file
    elif (
        len(ARGS.path_file) > 1
    ):  # It must be a list of files (e.g. 1.mkv 2.mp4) or a wildcard (e.g. *.avi)
        if all(
            os.path.isfile(name) for name in ARGS.path_file
        ):  # Check if all of inputs are files.
            files = ARGS.path_file
        else:
            raise FileExistsError("With multiple inputs you must provide only files.")
    elif os.path.isdir((directory := ARGS.path_file[0])):
        if ARGS.recursive:
            files = [
                os.path.join(os.path.relpath(path), file)
                for path, _, files_list in os.walk(top=directory)
                for file in files_list
            ]
        else:
            os.chdir(directory)
            files = [file for file in os.listdir() if os.path.isfile(file)]
    else:  # in case of a single invalid argument (e.g. viddur fake) we should fail.
        raise NotADirectoryError(f"{directory!r} is not a valid directory or filename.")

    return files


async def main() -> int:
    files = cleanup_inputs()
    sem = asyncio.Semaphore(SEM_NUM)
    tasks = [asyncio.create_task(calc_with_cautious(file, sem)) for file in files]
    results = await asyncio.gather(*tasks)
    if tasks:
        if ARGS.sort or ARGS.reverse:
            sorted_msgs()
        return any(
            results
        )  # Check to see if any of the checked file is failed; for the return code.
    return 1  # bad arguments -> returning failure return code.


if __name__ == "__main__":
    assert check_ffprobe(), '"ffprobe" is not found.'
    ARGS = parsing_args()
    exit_code = asyncio.run(main())
    prefix = "" if ARGS.quiet else "\nTotal Time is: "
    print(prefix + format_time(TOTAL))
    sys.exit(exit_code)
