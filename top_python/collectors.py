"""프로세스/CPU/메모리/로드 평균 수집 로직."""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import psutil

from top_python.formatting import ema_step, priority_label, to_mib
from top_python.models import ProcCacheEntry, ProcessRow


class ProcessCollector:
    def __init__(self) -> None:
        self._cache: Dict[int, ProcCacheEntry] = {}

    def collect(self, show_cmdline: bool = False) -> Tuple[List[ProcessRow], dict]:
        rows: List[ProcessRow] = []
        now = time.time()
        states = {"running": 0, "sleeping": 0, "stopped": 0, "zombie": 0, "other": 0}

        attrs = ["pid", "name", "username", "nice", "status", "memory_percent", "memory_info", "cpu_times"]
        for proc in psutil.process_iter(attrs):
            try:
                pid = proc.pid
                if pid <= 0:
                    continue

                entry = self._cache.get(pid)
                if entry is None:
                    entry = ProcCacheEntry(proc=proc)
                    self._cache[pid] = entry
                else:
                    entry.proc = proc

                entry.last_seen = now
                with proc.oneshot():
                    info = proc.info
                    if entry.user == "?":
                        entry.user = (info.get("username") or "?")[:8]
                    if entry.cmd == "?":
                        entry.cmd = info.get("name") or "?"

                    status = info.get("status") or "unknown"
                    mem_info = info.get("memory_info")
                    cpu_times = info.get("cpu_times")
                    nice_value = info.get("nice")
                    mem_percent = info.get("memory_percent") or 0.0

                if not entry.primed:
                    proc.cpu_percent(interval=0.0)
                    entry.primed = True
                    cpu = 0.0
                else:
                    cpu = proc.cpu_percent(interval=None)

                if status == psutil.STATUS_RUNNING:
                    states["running"] += 1
                elif status in (psutil.STATUS_SLEEPING, psutil.STATUS_DISK_SLEEP):
                    states["sleeping"] += 1
                elif status in (psutil.STATUS_STOPPED, psutil.STATUS_TRACING_STOP):
                    states["stopped"] += 1
                elif status == psutil.STATUS_ZOMBIE:
                    states["zombie"] += 1
                else:
                    states["other"] += 1

                cpu_time_sum = 0.0
                if cpu_times:
                    cpu_time_sum = float(getattr(cpu_times, "user", 0.0) + getattr(cpu_times, "system", 0.0))

                nice_value = int(nice_value) if isinstance(nice_value, (int, float)) else 0

                rows.append(
                    ProcessRow(
                        pid=pid,
                        user=entry.user,
                        pr=priority_label(nice_value),
                        ni=nice_value,
                        virt=to_mib(getattr(mem_info, "vms", 0)),
                        res=to_mib(getattr(mem_info, "rss", 0)),
                        shr=to_mib(getattr(mem_info, "shared", 0)),
                        state=(status[:1] or "?").upper(),
                        cpu=max(float(cpu), 0.0),
                        mem=max(float(mem_percent), 0.0),
                        timep=cpu_time_sum,
                        cmd=entry.cmd,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        stale = [pid for pid, entry in self._cache.items() if now - entry.last_seen > 2.0]
        for pid in stale:
            self._cache.pop(pid, None)

        return rows, states


def cpu_breakdown() -> dict:
    times = psutil.cpu_times_percent(interval=None)
    return {
        "us": getattr(times, "user", 0.0),
        "sy": getattr(times, "system", 0.0),
        "ni": getattr(times, "nice", 0.0),
        "id": getattr(times, "idle", 0.0),
        "wa": getattr(times, "iowait", 0.0),
        "hi": getattr(times, "irq", 0.0),
        "si": getattr(times, "softirq", 0.0),
        "st": getattr(times, "steal", 0.0),
    }


def memory_snapshot() -> dict:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cached = getattr(vm, "cached", 0)
    buffers = getattr(vm, "buffers", 0)
    buff_cache = cached + buffers
    return {
        "mem_total": vm.total,
        "mem_free": vm.available,
        "mem_used": max(vm.total - vm.available, 0),
        "buff_cache": buff_cache,
        "swap_total": swap.total,
        "swap_free": swap.free,
        "swap_used": swap.used,
    }


class LoadAverageTracker:
    _TAUS = (60.0, 300.0, 900.0)

    def __init__(self, cpu_count: int) -> None:
        self.cpu_count = cpu_count
        self._ema: List[float] = [0.0, 0.0, 0.0]

    def update(self, cpu_used: float, dt: float) -> List[float]:
        pseudo_load = (cpu_used / 100.0) * self.cpu_count
        self._ema = [
            ema_step(prev, pseudo_load, dt, tau)
            for prev, tau in zip(self._ema, self._TAUS)
        ]
        return list(self._ema)
