from unittest.mock import AsyncMock, Mock

import pytest
from conftest import (
    MockedParser,
    checking_args_params,
    find_duration_params,
    format_params,
    handle_params,
)

import viddur.source as viddur


def test_default_terminal_width():
    result = viddur.default_terminal_width()
    assert isinstance(result, int)


def test_check_ffprobe(monkeypatch):
    monkeypatch.setattr(viddur.shutil, "which", lambda _: None)
    assert not viddur.check_ffprobe()
    monkeypatch.setattr(viddur.shutil, "which", lambda _: "Some Path")
    assert viddur.check_ffprobe()


@pytest.mark.parametrize(
    "simple_output", (False, True), ids=("Simple_Output: False", "Simple_Output: True")
)
def test_pretty_print(capsys, mocked_raw_args, simple_output):
    mocked_raw_args.width = 80
    mocked_raw_args.simple_output = simple_output
    viddur.pretty_print("file", "some Detail!", mocked_raw_args)
    out, _ = capsys.readouterr()
    assert "some Detail!" in out


@pytest.mark.parametrize(("seconds", "f", "expected"), format_params)
def test_format_time(mocked_raw_args, seconds, f, expected):
    mocked_raw_args.f = mocked_raw_args.format = f
    out = viddur.format_time(seconds, mocked_raw_args)
    assert out == expected


@pytest.mark.parametrize(
    ("verbose", "sort", "reverse", "expected"), checking_args_params
)
def test_checking_args(monkeypatch, mocked_raw_args, verbose, sort, reverse, expected):
    mocked_raw_args.v = mocked_raw_args.verbose = verbose
    mocked_raw_args.s = mocked_raw_args.sort = sort
    mocked_raw_args.reverse = reverse

    mocked_parser = MockedParser(mocked_raw_args)

    if expected:
        with pytest.raises(SystemExit):
            viddur.checking_args(mocked_parser)
    else:
        assert mocked_raw_args == viddur.checking_args(mocked_parser)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("return_value", "return_code", "expected"), find_duration_params
)
async def test_find_duration(monkeypatch, return_value, return_code, expected):
    process = Mock()
    process.communicate = AsyncMock(return_value=(return_value, None))
    process.returncode = return_code
    async_mock = AsyncMock(return_value=process)
    monkeypatch.setattr(viddur.asyncio, "create_subprocess_shell", async_mock)
    result = await viddur.find_duration("test")
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "file_name",
        "args",
        "result",
        "expected_return_code",
        "expected_output",
        "expected_to_saved",
    ),
    handle_params,
)
async def test_handle(
    monkeypatch,
    capsys,
    file_name,
    args,
    result,
    expected_return_code,
    expected_output,
    expected_to_saved,
):
    semaphore = viddur.asyncio.Semaphore(1)
    monkeypatch.setattr(viddur, "find_duration", AsyncMock(return_value=result))
    return_code = await viddur.handle(file_name, semaphore, args)
    assert return_code == expected_return_code
    if expected_to_saved:
        if return_code == 0:
            if "bad" in file_name and not args.all and not (args.sort or args.reverse):
                assert file_name not in viddur.FILES_DUR.keys()
            else:
                if "bad" in file_name and not args.all:
                    assert viddur.FILES_DUR[file_name] == 0.0
                else:
                    assert viddur.FILES_DUR[file_name] == result
        else:
            assert viddur.FILES_DUR[file_name] == 0.0
    else:
        assert file_name not in viddur.FILES_DUR.keys()
    out, _ = capsys.readouterr()
    if expected_output:
        assert out != ""
    else:
        assert out == ""


@pytest.mark.cleanup_inputs
def test_cleanup_inputs_without_argument(mocked_directory, mocked_raw_args):
    mocked_raw_args.path_file = [viddur.os.getcwd()]
    result = viddur.cleanup_inputs(mocked_raw_args)
    assert list(result) == [
        "pwd_bad_1.mp3",
        "pwd_bad_2.pdf",
        "pwd_correct_1.mp4",
        "pwd_correct_2.mkv",
    ]


@pytest.mark.cleanup_inputs
def test_cleanup_inputs_with_one_file(mocked_directory, mocked_raw_args):
    mocked_raw_args.path_file = ["pwd_correct_1.mp4"]
    result = viddur.cleanup_inputs(mocked_raw_args)
    assert list(result) == mocked_raw_args.path_file


@pytest.mark.cleanup_inputs
def test_cleanup_inputs_with_two_file(mocked_directory, mocked_raw_args):
    mocked_raw_args.path_file = ["pwd_correct_1.mp4", "pwd_bad_1.mp3"]
    result = viddur.cleanup_inputs(mocked_raw_args)
    assert list(result) == mocked_raw_args.path_file


@pytest.mark.cleanup_inputs
def test_cleanup_inputs_with_one_dir_one_file(mocked_directory, mocked_raw_args):
    mocked_raw_args.path_file = ["pwd_correct_1.mp4", "dir1"]
    with pytest.raises(FileExistsError):
        viddur.cleanup_inputs(mocked_raw_args)


@pytest.mark.cleanup_inputs
def test_cleanup_inputs_with_two_dirs(mocked_directory, mocked_raw_args):
    mocked_raw_args.path_file = ["dir2", "dir1"]
    with pytest.raises(FileExistsError):
        viddur.cleanup_inputs(mocked_raw_args)


@pytest.mark.cleanup_inputs
def test_cleanup_inputs_with_recursive_with_file(mocked_directory, mocked_raw_args):
    mocked_raw_args.recursive = True
    mocked_raw_args.path_file = ["pwd_correct_1.mp4"]
    with pytest.raises(NotADirectoryError):
        viddur.cleanup_inputs(mocked_raw_args)


@pytest.mark.cleanup_inputs
def test_cleanup_inputs_with_recursive(mocked_directory, mocked_raw_args):
    mocked_raw_args.recursive = True
    mocked_raw_args.path_file = [viddur.os.getcwd()]
    result = viddur.cleanup_inputs(mocked_raw_args)
    assert list(result) == [
        "./pwd_bad_1.mp3",
        "./pwd_bad_2.pdf",
        "./pwd_correct_1.mp4",
        "./pwd_correct_2.mkv",
        "dir2/dir2_correct_2.mkv",
        "dir2/dir2_correct_1.mp4",
        "dir2/dir2_bad_2.pdf",
        "dir2/dir2_bad_1.mp3",
        "dir1/dir1_bad_1.mp3",
        "dir1/dir1_bad_2.pdf",
        "dir1/dir1_correct_1.mp4",
        "dir1/dir1_correct_2.mkv",
        "dir1/dir3/dir3_correct_2.mkv",
        "dir1/dir3/dir3_bad_1.mp3",
        "dir1/dir3/dir3_bad_2.pdf",
        "dir1/dir3/dir3_correct_1.mp4",
    ]


@pytest.mark.cleanup_inputs
def test_cleanup_inputs_with_recursive_with_dir(mocked_directory, mocked_raw_args):
    mocked_raw_args.recursive = True
    mocked_raw_args.path_file = ["dir1"]
    result = viddur.cleanup_inputs(mocked_raw_args)
    assert list(result) == [
        "dir1/dir1_bad_1.mp3",
        "dir1/dir1_bad_2.pdf",
        "dir1/dir1_correct_1.mp4",
        "dir1/dir1_correct_2.mkv",
        "dir1/dir3/dir3_correct_2.mkv",
        "dir1/dir3/dir3_bad_1.mp3",
        "dir1/dir3/dir3_bad_2.pdf",
        "dir1/dir3/dir3_correct_1.mp4",
    ]


@pytest.mark.cleanup_inputs
def test_cleanup_inputs_with_bad_input(mocked_directory, mocked_raw_args):
    mocked_raw_args.recursive = True
    mocked_raw_args.path_file = ["unknown"]
    with pytest.raises(NotADirectoryError):
        viddur.cleanup_inputs(mocked_raw_args)
