"""화면 섹션별 렌더링 순수 함수 모음."""

from __future__ import annotations

from typing import List, Optional, Tuple

from top_python.colors import FG_BLUE, FG_CYAN, FG_MAGENTA, FG_RED, FG_WHITE, bar, color, metric_color, state_color
from top_python.formatting import format_time_plus, to_mib
from top_python.models import ProcessRow


def render_header(now: str, uptime: str, loads: Tuple[float, float, float], enabled: bool) -> str:
    load1, load5, load15 = loads
    head = f"top - {now} up {uptime},  load average: {load1:.2f}, {load5:.2f}, {load15:.2f}"
    return color(head, FG_BLUE, bold=True, enabled=enabled)


def render_tasks_section(states: dict) -> str:
    return (
        "Tasks: "
        f"{sum(states.values()):>4} total, "
        f"{states['running']:>3} running, "
        f"{states['sleeping']:>3} sleeping, "
        f"{states['stopped']:>3} stopped, "
        f"{states['zombie']:>3} zombie"
    )


def render_cpu_section(cpu: dict, enabled: bool) -> List[str]:
    cpu_used = max(0.0, 100.0 - cpu["id"])
    cpu_line = (
        "%Cpu(s): "
        f"{cpu['us']:>5.1f} us, {cpu['sy']:>5.1f} sy, {cpu['ni']:>5.1f} ni, "
        f"{cpu['id']:>5.1f} id, {cpu['wa']:>5.1f} wa, {cpu['hi']:>5.1f} hi, "
        f"{cpu['si']:>5.1f} si, {cpu['st']:>5.1f} st"
    )
    bar_line = f"CPU  {bar(cpu_used, enabled=enabled)} {cpu_used:5.1f}%"
    return [cpu_line, bar_line]


def render_mem_section(mem: dict, enabled: bool) -> List[str]:
    mem_pct = (mem["mem_used"] / mem["mem_total"] * 100.0) if mem["mem_total"] else 0.0
    mem_line = (
        "MiB Mem : "
        f"{to_mib(mem['mem_total']):>8.1f} total, "
        f"{to_mib(mem['mem_free']):>8.1f} free, "
        f"{to_mib(mem['mem_used']):>8.1f} used, "
        f"{to_mib(mem['buff_cache']):>8.1f} buff/cache"
    )
    bar_line = f"MEM  {bar(mem_pct, enabled=enabled)} {mem_pct:5.1f}%"
    swap_line = (
        "MiB Swap: "
        f"{to_mib(mem['swap_total']):>8.1f} total, "
        f"{to_mib(mem['swap_free']):>8.1f} free, "
        f"{to_mib(mem['swap_used']):>8.1f} used"
    )
    return [mem_line, bar_line, swap_line]


def render_process_table(rows: List[ProcessRow], width: int, enabled: bool) -> List[str]:
    lines = [
        color(
            "    PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND",
            FG_MAGENTA,
            bold=True,
            enabled=enabled,
        )
    ]

    for proc in rows:
        cpu_txt = f"{proc.cpu:>5.1f}"
        mem_txt = f"{proc.mem:>4.1f}"
        state_txt = f"{proc.state:>1}"

        cpu_colored = color(cpu_txt, metric_color(proc.cpu), enabled=enabled)
        mem_colored = color(mem_txt, metric_color(proc.mem), enabled=enabled)
        state_colored = color(state_txt, state_color(proc.state), bold=(proc.state == "R"), enabled=enabled)
        cmd_color = FG_RED if proc.cpu >= 50.0 else FG_WHITE
        cmd_colored = color(proc.cmd[: max(5, width - 75)], cmd_color, enabled=enabled)

        lines.append(
            f"{proc.pid:>7} "
            f"{proc.user:<8} "
            f"{proc.pr:>2} "
            f"{proc.ni:>3} "
            f"{proc.virt:>7.1f} "
            f"{proc.res:>6.1f} "
            f"{proc.shr:>6.1f} "
            f"{state_colored} "
            f"{cpu_colored} "
            f"{mem_colored} "
            f"{format_time_plus(proc.timep):>9} "
            f"{cmd_colored}"
        )

    return lines


def core_rows(percpu_values: List[float], per_row: int = 4, enabled: bool = True) -> List[str]:
    lines = []
    for start in range(0, len(percpu_values), per_row):
        chunk = percpu_values[start : start + per_row]
        parts = [
            f"{start + i:>2}{bar(value, width=10, enabled=enabled)}{value:5.1f}%"
            for i, value in enumerate(chunk)
        ]
        lines.append(" ".join(parts))
    return lines


def build_screen(
    rows: List[ProcessRow],
    states: dict,
    cpu: dict,
    mem: dict,
    width: int,
    height: int,
    now: str,
    uptime: str,
    loads: Tuple[float, float, float],
    update_interval: float,
    enabled: bool = True,
    show_percpu: bool = False,
    percpu_values: Optional[List[float]] = None,
) -> str:
    core_lines = core_rows(percpu_values, enabled=enabled) if show_percpu and percpu_values else []
    max_proc_rows = max(5, height - 11 - len(core_lines))

    lines = [render_header(now, uptime, loads, enabled)]
    lines.append(render_tasks_section(states))
    lines.extend(render_cpu_section(cpu, enabled))
    lines.extend(core_lines)
    lines.extend(render_mem_section(mem, enabled))
    lines.append("")
    lines.extend(render_process_table(rows[:max_proc_rows], width, enabled))
    lines.append("")
    lines.append(
        color(
            f"Keys: q quit | c cpu | m mem | p pid | t time | r reverse | interval {update_interval:.1f}s",
            FG_CYAN,
            enabled=enabled,
        )
    )

    if enabled:
        frame = "\n".join(lines)
    else:
        frame = "\n".join(line[:width].ljust(width) for line in lines)
    return f"\033[H\033[J{frame}"
