"""순수 포맷팅/계산 함수 모음 (SystemMonitor 상태에 의존하지 않음)."""

from __future__ import annotations

import math


def format_uptime(seconds: float) -> str:
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        unit = "day" if days == 1 else "days"
        return f"{days} {unit}, {hours:02d}:{minutes:02d}"
    return f"{hours:02d}:{minutes:02d}"


def to_mib(value_bytes: int) -> float:
    return value_bytes / (1024 * 1024)


def priority_label(nice_value: int) -> str:
    return str(20 + nice_value)


def format_time_plus(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:>4d}:{secs:05.2f}"


def ema_step(prev: float, target: float, dt: float, tau: float) -> float:
    alpha = 1 - math.exp(-dt / tau)
    return prev + alpha * (target - prev)
