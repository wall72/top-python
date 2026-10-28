from top_python.cli import parse_args
import pytest


def test_parse_args_defaults():
    args = parse_args([])
    assert args.no_color is False
    assert args.interval == 1.0


def test_parse_args_no_color_flag():
    args = parse_args(["--no-color"])
    assert args.no_color is True


def test_parse_args_interval_value():
    args = parse_args(["--interval", "2.5"])
    assert args.interval == 2.5


def test_parse_args_rejects_non_positive_interval():
    with pytest.raises(SystemExit):
        parse_args(["--interval", "0"])


def test_parse_args_rejects_non_numeric_interval():
    with pytest.raises(SystemExit):
        parse_args(["--interval", "abc"])


def test_version_flag_exits_zero(capsys):
    from top_python import __version__

    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out
