"""ProcessRow 목록 정렬 순수 함수."""

from __future__ import annotations

import heapq
from typing import List, Optional

from top_python.models import ProcessRow

_KEY_MAP = {
    "cpu": lambda row: row.cpu,
    "mem": lambda row: row.mem,
    "pid": lambda row: row.pid,
    "time": lambda row: row.timep,
}


def sort_rows(rows: List[ProcessRow], sort_key: str, reverse: bool, limit: Optional[int] = None) -> List[ProcessRow]:
    key_fn = _KEY_MAP.get(sort_key, _KEY_MAP["cpu"])
    if limit is not None and limit > 0:
        if reverse:
            return heapq.nlargest(limit, rows, key=key_fn)
        return heapq.nsmallest(limit, rows, key=key_fn)
    return sorted(rows, key=key_fn, reverse=reverse)
