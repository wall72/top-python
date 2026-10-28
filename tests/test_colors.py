from top_python.colors import color, metric_color, state_color, bar, FG_RED, FG_GREEN


def test_color_disabled_returns_plain_text():
    assert color("hi", FG_RED, enabled=False) == "hi"


def test_color_enabled_wraps_with_code():
    assert color("hi", FG_RED, enabled=True) == f"{FG_RED}hi\033[0m"


def test_metric_color_thresholds():
    assert metric_color(10.0) == FG_GREEN
    assert metric_color(90.0) == FG_RED


def test_state_color_running_is_green():
    assert state_color("R") == FG_GREEN


def test_bar_disabled_has_no_escape_codes():
    result = bar(50.0, width=10, enabled=False)
    assert "\033" not in result
    assert result.count("#") == 5
