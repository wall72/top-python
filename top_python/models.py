"""프로세스 수집에 쓰이는 데이터클래스 정의."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import psutil


@dataclass
class ProcCacheEntry:
    proc: psutil.Process
    primed: bool = False
    last_seen: float = 0.0
    user: str = "?"
    cmd: str = "?"
    cmdline_full: Optional[str] = None


@dataclass
class ProcessRow:
    pid: int
    user: str
    pr: str
    ni: int
    virt: float
    res: float
    shr: float
    state: str
    cpu: float
    mem: float
    timep: float
    cmd: str
