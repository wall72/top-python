"""플랫폼 종속 터미널 키보드 입력 처리."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Optional


def read_key() -> Optional[str]:
    if os.name == "nt":
        try:
            import msvcrt

            if msvcrt.kbhit():
                return msvcrt.getch().decode("utf-8", errors="ignore").lower()
        except Exception:
            return None
        return None

    try:
        import select

        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1).lower()
    except Exception:
        return None
    return None


@contextmanager
def raw_stdin():
    if os.name == "nt":
        yield
        return
    try:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            yield
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        yield
