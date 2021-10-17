from collections import namedtuple
from unittest.mock import Mock

import pytest

import viddur.source as viddur


def args_gen():
    args = type("args", (), {})

    arguments = (
        "path_file",
        "a",
        "all",
        "f",
        "format",
        "r",
        "recursive",
        "sem",
        "semaphore",
        "w",
        "width",
        "simple_output",
        "v",
        "verbose",
        "q",
        "quiet",
        "s",
        "sort",
        "reverse",
    )

    for arg in arguments:
        setattr(args, arg, False)

    return args


def all_args():
    args = args_gen()
    args.a = args.all = True
    return args


def verbose_args():
    args = args_gen()
    args.v = args.verbose = True
    return args


def sort_args():
    args = verbose_args()
    args.s = args.sort = True
    return args


def reverse_args():
    args = verbose_args()
    args.reverse = True
    return args


def all_verbose_args():
    args = all_args()
    args.v = args.verbose = True
    return args


def all_sort_args():
    args = all_verbose_args()
    args.s = args.sort = True
    return args


def all_reverse_args():
    args = all_verbose_args()
    args.reverse = True
    return args


@pytest.fixture()
def mocked_raw_args():
    return args_gen()


@pytest.fixture()
def mocked_directory(tmpdir):
    pwd = tmpdir.mkdir("pwd")
    pwd.join("pwd_correct_1.mp4").write(b"Some nonsense")
    pwd.join("pwd_correct_2.mkv").write(b"Some nonsense")
    pwd.join("pwd_bad_1.mp3").write(b"Some nonsense")
    pwd.join("pwd_bad_2.pdf").write(b"Some nonsense")

    dir1 = pwd.mkdir("dir1")
    dir1.join("dir1_correct_1.mp4").write(b"Some nonsense")
    dir1.join("dir1_correct_2.mkv").write(b"Some nonsense")
    dir1.join("dir1_bad_1.mp3").write(b"Some nonsense")
    dir1.join("dir1_bad_2.pdf").write(b"Some nonsense")

    dir2 = pwd.mkdir("dir2")
    dir2.join("dir2_correct_1.mp4").write(b"Some nonsense")
    dir2.join("dir2_correct_2.mkv").write(b"Some nonsense")
    dir2.join("dir2_bad_1.mp3").write(b"Some nonsense")
    dir2.join("dir2_bad_2.pdf").write(b"Some nonsense")

    dir3 = dir1.mkdir("dir3")
    dir3.join("dir3_correct_1.mp4").write(b"Some nonsense")
    dir3.join("dir3_correct_2.mkv").write(b"Some nonsense")
    dir3.join("dir3_bad_1.mp3").write(b"Some nonsense")
    dir3.join("dir3_bad_2.pdf").write(b"Some nonsense")

    _ = dir3.mkdir("dir4")

    viddur.os.chdir(pwd)


class MockedParser:
    def __init__(self, return_value):
        self.return_value = return_value

    def parse_args(self):
        return self.return_value

    @staticmethod
    def error(msg):
        # viddur.argparse.ArgumentParser().error(msg)
        raise SystemExit(msg)


format_params = (
    pytest.param(100.0, "s", "100.000s", id="100s"),
    pytest.param(100.2, "s", "100.200s", id="100.2s"),
    pytest.param(100.2345, "s", "100.234s", id="100.2345s"),
    pytest.param(100.0, None, "00:01:40", id="100 None"),
    pytest.param(100.0, "default", "00:01:40", id="100 default"),
    pytest.param(285120.0, None, "3 day, 07:12:00", id="default large"),
    pytest.param(100.0, "m", "1.667m", id="minute"),
    pytest.param(100.0, "h", "0.028h", id="hour"),
    pytest.param(1234.0, "d", "0.014d", id="days"),
)

checking_args_params = (
    pytest.param(True, True, False, False, id="--Verbose --Sort"),
    pytest.param(True, False, False, False, id="--Verbose"),
    pytest.param(False, False, False, False, id="Empty"),
    pytest.param(False, True, False, True, id="--Sort without --Verbose"),
    pytest.param(False, True, True, True, id="--Sort --Reverse without --Verbose"),
    pytest.param(False, False, True, True, id="--Reverse without --Verbose"),
)

find_duration_params = (
    pytest.param(0.0, 0, False, id="0. -> False"),
    pytest.param(0.0, 0, False, id="0., ReturnCode: 0 -> False"),
    pytest.param(b"N/A\n", 0, False, id="NaN -> False"),
    pytest.param(1.0, 1, False, id="0. -> False"),
    pytest.param(1.0, 0, 1.0, id="0. -> False"),
)


handle_params = (
    pytest.param("1_correct.mkv", args_gen(), 100.0, 0, False, True),
    pytest.param("2_correct.mp4", args_gen(), 100.0, 0, False, True),
    pytest.param("3_bad.mp3", args_gen(), 100.0, 0, False, False),
    pytest.param("4_bad.mp3", all_args(), 0.0, 1, True, False),
    pytest.param("5_correct.mp4", args_gen(), 0.0, 1, True, False),
    pytest.param("6_bad.mp3", verbose_args(), 0.0, 0, True, False),
    pytest.param("7_correct.mkv", all_args(), 100.0, 0, False, True),
    pytest.param("8_correct.mp4", verbose_args(), 0.0, 1, True, False),
    pytest.param("9_correct.mp4", sort_args(), 100.0, 0, False, True),
    pytest.param("10_correct.mp4", verbose_args(), 100.0, 0, True, True),
    pytest.param("11_correct.mp4", reverse_args(), 100.0, 0, False, True),
    pytest.param("12_correct.mp4", reverse_args(), 0.0, 1, False, True),
    pytest.param("13_bad.wav", all_args(), 100.0, 0, False, True),
    pytest.param("14_bad.mp3", all_verbose_args(), 100.0, 0, True, True),
    pytest.param("15_correct.mp4", all_sort_args(), 0.0, 1, False, True),
    pytest.param("16_bad.mp3", sort_args(), 0.0, 0, False, True),
    pytest.param("17_bad.mp3", reverse_args(), 100.0, 0, False, True),
)
