import os
import mimetypes
import time
import asyncio
import argparse
import sys


TOTAL = 0
FILES_DUR = {}
WIDTH = 0
COMMAND = (
    'ffprobe -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{}"'
)


def summerize_filename(filename):
    if len(filename) > (proper := ((WIDTH // 2) + 5)):
        return filename[:proper] + " ..."
    return filename


def checking_args(args, parser):
    if not args.verbose:
        if args.sort or args.reverse:
            parser.error(
                "You should use -v (--verbose) argument first for getting the output sorted"
            )
    return args


def parsing_args():
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


def format_time(seconds):
    gm_time = time.gmtime(seconds)
    res = ""
    if (day := gm_time.tm_mday) > 1:
        res = f"{day - 1} day, "
    return res + time.strftime("%H:%M:%S", gm_time)


async def calc(file):
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

        if not process.returncode and stdout != b"N/A\n":
            duration = float(stdout)
            TOTAL += float(stdout)

            if ARGS.verbose:
                if not (ARGS.sort or ARGS.reverse):
                    print(
                        f'{f"{summerize_filename(file)!r}:":<{WIDTH}} {format_time(duration)}'
                    )
                else:
                    FILES_DUR[file] = duration
        else:
            if not ARGS.quiet:
                print(
                    f'{f"{summerize_filename(file)!r}:":<{WIDTH}} cannot get examined.'
                )
    else:
        if ARGS.verbose:
            if not (ARGS.sort or ARGS.reverse):
                print(
                    f'{f"{summerize_filename(file)!r}:":<{WIDTH}} is not recognized as a media.'
                )
            else:
                FILES_DUR[file] = False
        return 1

    return process.returncode


def sorted_msgs():
    sorted_dict = {
        k: v
        for k, v in sorted(
            FILES_DUR.items(),
            key=lambda x: x[1],
            reverse=True if ARGS.reverse else False,
        )
    }
    for k, v in sorted_dict.items():
        if v:
            print(f'{f"{summerize_filename(k)!r}:":<{WIDTH}} {format_time(v)}')
        else:
            print(f'{f"{summerize_filename(k)!r}:":<{WIDTH}} cannot get examined.')


async def main():
    global WIDTH

    if len(ARGS.path_file) > 1 or os.path.isfile(ARGS.path_file[0]):
        files = ARGS.path_file
    else:
        files = os.listdir(ARGS.path_file[0])

    WIDTH = len(max(files, key=len)) + 5
    WIDTH = min(WIDTH, os.get_terminal_size()[0] // 2) + 1

    tasks = [asyncio.create_task(calc(file)) for file in files if os.path.isfile(file)]
    results = await asyncio.gather(*tasks)
    if tasks:
        if ARGS.sort or ARGS.reverse:
            sorted_msgs()
        return any(results)
    return 1


if __name__ == "__main__":
    ARGS = parsing_args()
    exit_code = asyncio.run(main())
    prefix = "" if ARGS.quiet else "\nTotal Time is: "
    print(prefix + format_time(TOTAL))
    sys.exit(exit_code)
