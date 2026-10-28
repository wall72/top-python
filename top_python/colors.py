"""ANSI 색상 상수와 순수 색상/막대 포맷팅 함수 모음."""

from __future__ import annotations

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
FG_CYAN = "\033[36m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_RED = "\033[31m"
FG_BLUE = "\033[34m"
FG_MAGENTA = "\033[35m"
FG_WHITE = "\033[37m"


def color(text: str, code: str, bold: bool = False, enabled: bool = True) -> str:
    if not enabled:
        return text
    if bold:
        return f"{BOLD}{code}{text}{RESET}"
    return f"{code}{text}{RESET}"


def metric_color(value: float) -> str:
    if value >= 80.0:
        return FG_RED
    if value >= 50.0:
        return FG_YELLOW
    return FG_GREEN


def state_color(state: str) -> str:
    if state == "R":
        return FG_GREEN
    if state == "S":
        return FG_CYAN
    if state in ("D", "T"):
        return FG_YELLOW
    if state == "Z":
        return FG_RED
    return FG_WHITE


def bar(percent: float, width: int = 24, enabled: bool = True) -> str:
    p = max(0.0, min(percent, 100.0))
    filled = int((p / 100.0) * width)
    bar_text = "|" + ("#" * filled) + ("." * (width - filled)) + "|"
    return color(bar_text, metric_color(p), bold=False, enabled=enabled)
