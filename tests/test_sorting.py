from top_python.models import ProcessRow
from top_python.sorting import sort_rows


def _row(pid, cpu, mem, timep):
    return ProcessRow(pid=pid, user="u", pr="20", ni=0, virt=0, res=0, shr=0,
                       state="R", cpu=cpu, mem=mem, timep=timep, cmd="x")


ROWS = [_row(1, 10.0, 1.0, 5.0), _row(2, 50.0, 2.0, 1.0), _row(3, 5.0, 9.0, 9.0)]


def test_sort_by_cpu_descending():
    result = sort_rows(ROWS, "cpu", reverse=True)
    assert [r.pid for r in result] == [2, 1, 3]


def test_sort_by_pid_ascending():
    result = sort_rows(ROWS, "pid", reverse=False)
    assert [r.pid for r in result] == [1, 2, 3]


def test_sort_with_limit_uses_top_n():
    result = sort_rows(ROWS, "mem", reverse=True, limit=2)
    assert [r.pid for r in result] == [3, 2]


def test_sort_unknown_key_defaults_to_cpu():
    result = sort_rows(ROWS, "bogus", reverse=True)
    assert [r.pid for r in result] == [2, 1, 3]
