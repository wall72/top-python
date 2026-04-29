#!/usr/bin/env python3
"""Linux-style top monitor with low-overhead process sampling and htop-like colors."""

from __future__ import annotations

import heapq
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List

import psutil


@dataclass
class ProcCacheEntry:
    proc: psutil.Process
    primed: bool = False
    last_seen: float = 0.0
    user: str = "?"
    cmd: str = "?"


class SystemMonitor:
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

    def __init__(self) -> None:
        self.running = True
        self.update_interval = 1.0
        self.sort_key = "cpu"
        self.sort_reverse = True

        self.boot_time = psutil.boot_time()
        self.cpu_count = psutil.cpu_count(logical=True) or 1
        self.proc_cache: Dict[int, ProcCacheEntry] = {}

        self._enable_ansi_on_windows()
        self._disable_output_buffering()
        self.enable_color = sys.stdout.isatty()

    def _enable_ansi_on_windows(self) -> None:
        if os.name != "nt":
            return
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass

    def _disable_output_buffering(self) -> None:
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(line_buffering=True)
        except Exception:
            pass

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        if days > 0:
            return f"{days} day, {hours:02d}:{minutes:02d}"
        return f"{hours:02d}:{minutes:02d}"

    @staticmethod
    def _to_mib(value_bytes: int) -> float:
        return value_bytes / (1024 * 1024)

    @staticmethod
    def _format_time_plus(seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:>4d}:{secs:05.2f}"

    def _term_size(self) -> os.terminal_size:
        try:
            return os.get_terminal_size()
        except OSError:
            return os.terminal_size((120, 40))

    def _loadavg(self, cpu_used: float) -> List[float]:
        if hasattr(os, "getloadavg"):
            try:
                return list(os.getloadavg())
            except OSError:
                pass
        pseudo_load = (cpu_used / 100.0) * self.cpu_count
        return [pseudo_load, pseudo_load, pseudo_load]

    def _cpu_breakdown(self) -> dict:
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

    def _memory_snapshot(self) -> dict:
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

    def _collect_process_rows(self) -> tuple[list, dict]:
        rows = []
        now = time.time()
        states = {"running": 0, "sleeping": 0, "stopped": 0, "zombie": 0, "other": 0}

        attrs = ["pid", "name", "username", "nice", "status", "memory_percent", "memory_info", "cpu_times"]
        for proc in psutil.process_iter(attrs):
            try:
                pid = proc.pid
                if pid <= 0:
                    continue

                entry = self.proc_cache.get(pid)
                if entry is None:
                    entry = ProcCacheEntry(proc=proc)
                    self.proc_cache[pid] = entry
                else:
                    entry.proc = proc

                entry.last_seen = now
                with proc.oneshot():
                    info = proc.info
                    if entry.user == "?":
                        entry.user = (info.get("username") or "?")[:8]
                    if entry.cmd == "?":
                        entry.cmd = info.get("name") or "?"

                    if not entry.primed:
                        proc.cpu_percent(interval=0.0)
                        entry.primed = True
                        cpu = 0.0
                    else:
                        cpu = proc.cpu_percent(interval=None)

                    status = info.get("status") or "unknown"
                    mem_info = info.get("memory_info")
                    cpu_times = info.get("cpu_times")
                    nice_value = info.get("nice")
                    mem_percent = info.get("memory_percent") or 0.0

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
                    {
                        "pid": pid,
                        "user": entry.user,
                        "pr": "rt" if nice_value < 0 else "20",
                        "ni": nice_value,
                        "virt": self._to_mib(getattr(mem_info, "vms", 0)),
                        "res": self._to_mib(getattr(mem_info, "rss", 0)),
                        "shr": self._to_mib(getattr(mem_info, "shared", 0)),
                        "state": (status[:1] or "?").upper(),
                        "cpu": max(float(cpu), 0.0),
                        "mem": max(float(mem_percent), 0.0),
                        "timep": cpu_time_sum,
                        "cmd": entry.cmd,
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        stale = [pid for pid, entry in self.proc_cache.items() if now - entry.last_seen > 2.0]
        for pid in stale:
            self.proc_cache.pop(pid, None)

        return rows, states

    def _sort_rows(self, rows: Iterable[dict], limit: int | None = None) -> List[dict]:
        key_map = {
            "cpu": lambda x: x["cpu"],
            "mem": lambda x: x["mem"],
            "pid": lambda x: x["pid"],
            "time": lambda x: x["timep"],
        }
        key_fn = key_map.get(self.sort_key, key_map["cpu"])
        if limit is not None and limit > 0:
            if self.sort_reverse:
                return heapq.nlargest(limit, rows, key=key_fn)
            return heapq.nsmallest(limit, rows, key=key_fn)
        return sorted(rows, key=key_fn, reverse=self.sort_reverse)

    def _color(self, text: str, color: str, bold: bool = False) -> str:
        if not self.enable_color:
            return text
        if bold:
            return f"{self.BOLD}{color}{text}{self.RESET}"
        return f"{color}{text}{self.RESET}"

    def _metric_color(self, value: float) -> str:
        if value >= 80.0:
            return self.FG_RED
        if value >= 50.0:
            return self.FG_YELLOW
        return self.FG_GREEN

    def _state_color(self, state: str) -> str:
        if state == "R":
            return self.FG_GREEN
        if state == "S":
            return self.FG_CYAN
        if state in ("D", "T"):
            return self.FG_YELLOW
        if state == "Z":
            return self.FG_RED
        return self.FG_WHITE

    def _bar(self, percent: float, width: int = 24) -> str:
        p = max(0.0, min(percent, 100.0))
        filled = int((p / 100.0) * width)
        bar = "|" + ("#" * filled) + ("." * (width - filled)) + "|"
        return self._color(bar, self._metric_color(p), bold=False)

    def _build_screen(
        self,
        rows: List[dict],
        states: dict,
        cpu: dict,
        mem: dict,
        width: int,
        height: int,
    ) -> str:
        max_proc_rows = max(5, height - 11)

        now = datetime.now().strftime("%H:%M:%S")
        uptime = self._format_uptime(time.time() - self.boot_time)
        cpu_used = max(0.0, 100.0 - cpu["id"])
        load1, load5, load15 = self._loadavg(cpu_used)
        mem_pct = (mem["mem_used"] / mem["mem_total"] * 100.0) if mem["mem_total"] else 0.0

        lines = []
        head = f"top - {now} up {uptime},  load average: {load1:.2f}, {load5:.2f}, {load15:.2f}"
        lines.append(self._color(head, self.FG_BLUE, bold=True))
        lines.append(
            "Tasks: "
            f"{sum(states.values()):>4} total, "
            f"{states['running']:>3} running, "
            f"{states['sleeping']:>3} sleeping, "
            f"{states['stopped']:>3} stopped, "
            f"{states['zombie']:>3} zombie"
        )
        cpu_line = (
            "%Cpu(s): "
            f"{cpu['us']:>5.1f} us, {cpu['sy']:>5.1f} sy, {cpu['ni']:>5.1f} ni, "
            f"{cpu['id']:>5.1f} id, {cpu['wa']:>5.1f} wa, {cpu['hi']:>5.1f} hi, "
            f"{cpu['si']:>5.1f} si, {cpu['st']:>5.1f} st"
        )
        lines.append(cpu_line)
        lines.append(f"CPU  {self._bar(cpu_used)} {cpu_used:5.1f}%")

        mem_line = (
            "MiB Mem : "
            f"{self._to_mib(mem['mem_total']):>8.1f} total, "
            f"{self._to_mib(mem['mem_free']):>8.1f} free, "
            f"{self._to_mib(mem['mem_used']):>8.1f} used, "
            f"{self._to_mib(mem['buff_cache']):>8.1f} buff/cache"
        )
        lines.append(mem_line)
        lines.append(f"MEM  {self._bar(mem_pct)} {mem_pct:5.1f}%")
        lines.append(
            "MiB Swap: "
            f"{self._to_mib(mem['swap_total']):>8.1f} total, "
            f"{self._to_mib(mem['swap_free']):>8.1f} free, "
            f"{self._to_mib(mem['swap_used']):>8.1f} used"
        )
        lines.append("")
        lines.append(
            self._color(
                "    PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND",
                self.FG_MAGENTA,
                bold=True,
            )
        )

        for proc in rows[:max_proc_rows]:
            cpu_txt = f"{proc['cpu']:>5.1f}"
            mem_txt = f"{proc['mem']:>4.1f}"
            state_txt = f"{proc['state']:>1}"

            cpu_colored = self._color(cpu_txt, self._metric_color(proc["cpu"]))
            mem_colored = self._color(mem_txt, self._metric_color(proc["mem"]))
            state_colored = self._color(state_txt, self._state_color(proc["state"]), bold=(proc["state"] == "R"))
            cmd_color = self.FG_RED if proc["cpu"] >= 50.0 else self.FG_WHITE
            cmd_colored = self._color(proc["cmd"][: max(5, width - 75)], cmd_color)

            lines.append(
                f"{proc['pid']:>7} "
                f"{proc['user']:<8} "
                f"{proc['pr']:>2} "
                f"{proc['ni']:>3} "
                f"{proc['virt']:>7.1f} "
                f"{proc['res']:>6.1f} "
                f"{proc['shr']:>6.1f} "
                f"{state_colored} "
                f"{cpu_colored} "
                f"{mem_colored} "
                f"{self._format_time_plus(proc['timep']):>9} "
                f"{cmd_colored}"
            )

        lines.append("")
        lines.append(
            self._color(
                f"Keys: q quit | c cpu | m mem | p pid | t time | r reverse | interval {self.update_interval:.1f}s",
                self.FG_CYAN,
            )
        )

        if self.enable_color:
            frame = "\n".join(lines)
        else:
            frame = "\n".join(line[:width].ljust(width) for line in lines)
        return f"\033[H\033[J{frame}"

    def _read_key(self) -> str | None:
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
    def _raw_stdin(self):
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

    def _handle_key(self, key: str) -> None:
        if key in ("q", "\x03"):
            self.running = False
        elif key == "c":
            self.sort_key = "cpu"
            self.sort_reverse = True
        elif key == "m":
            self.sort_key = "mem"
            self.sort_reverse = True
        elif key == "p":
            self.sort_key = "pid"
            self.sort_reverse = False
        elif key == "t":
            self.sort_key = "time"
            self.sort_reverse = True
        elif key == "r":
            self.sort_reverse = not self.sort_reverse

    def run(self) -> None:
        print("Starting linux-style system monitor (q to quit)...", flush=True)
        time.sleep(0.3)

        psutil.cpu_percent(interval=0.1)
        psutil.cpu_times_percent(interval=0.1)

        with self._raw_stdin():
            try:
                while self.running:
                    size = self._term_size()
                    width = max(size.columns, 80)
                    height = max(size.lines, 18)
                    max_proc_rows = max(5, height - 11)

                    rows, states = self._collect_process_rows()
                    rows = self._sort_rows(rows, limit=max_proc_rows)
                    cpu = self._cpu_breakdown()
                    mem = self._memory_snapshot()

                    screen = self._build_screen(rows, states, cpu, mem, width, height)
                    sys.stdout.write(screen)
                    sys.stdout.flush()

                    t0 = time.time()
                    while time.time() - t0 < self.update_interval:
                        key = self._read_key()
                        if key:
                            self._handle_key(key)
                            if not self.running or key in ("c", "m", "p", "t", "r"):
                                break
                        time.sleep(0.03)
            except KeyboardInterrupt:
                pass
            finally:
                sys.stdout.write("\033[0m\033[2J\033[H")
                sys.stdout.flush()
                print("Monitor exited.", flush=True)


def main() -> None:
    try:
        SystemMonitor().run()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
