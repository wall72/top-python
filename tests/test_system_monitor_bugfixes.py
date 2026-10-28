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


def test_ema_step_moves_toward_target():
    result = SystemMonitor._ema_step(prev=0.0, target=1.0, dt=60.0, tau=60.0)
    assert 0.6 < result < 0.64  # 1 - e^-1 ≈ 0.632


def test_ema_step_zero_dt_returns_prev():
    assert SystemMonitor._ema_step(prev=0.5, target=1.0, dt=0.0, tau=60.0) == 0.5


def test_ema_step_large_dt_approaches_target():
    result = SystemMonitor._ema_step(prev=0.0, target=2.0, dt=100000.0, tau=60.0)
    assert result == pytest.approx(2.0, abs=1e-6)
