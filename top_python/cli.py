"""명령행 인자 파싱 및 엔트리포인트."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from top_python.app import SystemMonitor
from top_python import __version__


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid float value: {value!r}") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"interval must be positive: {value!r}")
    return parsed


def parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="top-python")
    parser.add_argument("--no-color", action="store_true", default=False, help="색상 출력을 비활성화한다")
    parser.add_argument("--interval", type=_positive_float, default=1.0, help="갱신 주기(초), 기본 1.0")
    parser.add_argument("--version", action="version", version=f"top-python {__version__}")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        SystemMonitor(enable_color=not args.no_color, update_interval=args.interval).run()
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
