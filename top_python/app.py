"""SystemMonitor 애플리케이션 조립 — 수집/정렬/렌더링/입력 모듈을 엮는다."""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from typing import Optional

import psutil

from top_python.collectors import LoadAverageTracker, ProcessCollector, cpu_breakdown, memory_snapshot
from top_python.formatting import format_uptime
from top_python.input_handling import raw_stdin, read_key
from top_python.render import build_screen
from top_python.sorting import sort_rows


class SystemMonitor:
    def __init__(self, enable_color: Optional[bool] = None, update_interval: float = 1.0) -> None:
        self.running = True
        self.update_interval = update_interval
        self.sort_key = "cpu"
        self.sort_reverse = True
        self.show_cmdline = False
        self.show_percpu = False

        self.boot_time = psutil.boot_time()
        self.cpu_count = psutil.cpu_count(logical=True) or 1
        self._collector = ProcessCollector()
        self._load_tracker = LoadAverageTracker(self.cpu_count)

        self._enable_ansi_on_windows()
        self._disable_output_buffering()
        self.enable_color = enable_color if enable_color is not None else sys.stdout.isatty()

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

    def _term_size(self) -> os.terminal_size:
        try:
            return os.get_terminal_size()
        except OSError:
            return os.terminal_size((120, 40))

    def handle_key(self, key: str) -> None:
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
        elif key == "+":
            self.update_interval += 0.5
        elif key == "-":
            self.update_interval = max(0.5, self.update_interval - 0.5)
        elif key == "e":
            self.show_cmdline = not self.show_cmdline
        elif key == "1":
            self.show_percpu = not self.show_percpu

    def run(self) -> None:
        print("Starting linux-style system monitor (q to quit)...", flush=True)
        time.sleep(0.3)

        psutil.cpu_percent(interval=0.1)
        psutil.cpu_times_percent(interval=0.1)

        with raw_stdin():
            try:
                while self.running:
                    size = self._term_size()
                    width = max(size.columns, 80)
                    height = max(size.lines, 18)
                    max_proc_rows = max(5, height - 11)

                    rows, states = self._collector.collect(show_cmdline=self.show_cmdline)
                    rows = sort_rows(rows, self.sort_key, self.sort_reverse, limit=max_proc_rows)
                    cpu = cpu_breakdown()
                    mem = memory_snapshot()

                    now = datetime.now().strftime("%H:%M:%S")
                    uptime = format_uptime(time.time() - self.boot_time)
                    cpu_used = max(0.0, 100.0 - cpu["id"])
                    loads = tuple(self._load_tracker.update(cpu_used, self.update_interval))
                    percpu_values = psutil.cpu_percent(percpu=True, interval=None) if self.show_percpu else None

                    screen = build_screen(
                        rows,
                        states,
                        cpu,
                        mem,
                        width,
                        height,
                        now,
                        uptime,
                        loads,
                        self.update_interval,
                        enabled=self.enable_color,
                        show_percpu=self.show_percpu,
                        percpu_values=percpu_values,
                    )
                    sys.stdout.write(screen)
                    sys.stdout.flush()

                    t0 = time.time()
                    while time.time() - t0 < self.update_interval:
                        key = read_key()
                        if key:
                            self.handle_key(key)
                            if not self.running or key in ("c", "m", "p", "t", "r"):
                                break
                        time.sleep(0.03)
            except KeyboardInterrupt:
                pass
            finally:
                sys.stdout.write("\033[0m\033[2J\033[H")
                sys.stdout.flush()
                print("Monitor exited.", flush=True)
