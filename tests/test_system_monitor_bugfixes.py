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
