import pytest
from system_monitor import SystemMonitor


def test_priority_label_normal_nice():
    assert SystemMonitor._priority_label(0) == "20"


def test_priority_label_negative_nice():
    assert SystemMonitor._priority_label(-5) == "15"


def test_priority_label_min_nice():
    assert SystemMonitor._priority_label(-20) == "0"


def test_priority_label_max_nice():
    assert SystemMonitor._priority_label(19) == "39"


def test_format_uptime_singular_day():
    assert SystemMonitor._format_uptime(90000) == "1 day, 01:00"


def test_format_uptime_plural_days():
    assert SystemMonitor._format_uptime(2 * 86400 + 3600) == "2 days, 01:00"


def test_format_uptime_no_days():
    assert SystemMonitor._format_uptime(3661) == "01:01"
