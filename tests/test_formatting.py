from top_python.formatting import format_uptime, format_time_plus, to_mib, priority_label, ema_step
import pytest


def test_format_uptime_plural_days():
    assert format_uptime(2 * 86400 + 3600) == "2 days, 01:00"


def test_format_time_plus_basic():
    assert format_time_plus(83.45) == "   1:23.45"


def test_to_mib():
    assert to_mib(1024 * 1024 * 2) == 2.0


def test_priority_label_negative_nice():
    assert priority_label(-5) == "15"


def test_ema_step_zero_dt_returns_prev():
    assert ema_step(prev=0.5, target=1.0, dt=0.0, tau=60.0) == 0.5
