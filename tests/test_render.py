from top_python.render import render_header, render_process_table, core_rows
from top_python.models import ProcessRow


def test_render_header_contains_load_average():
    result = render_header("12:00:00", "01:00", (1.0, 0.5, 0.2), enabled=False)
    assert "load average: 1.00, 0.50, 0.20" in result


def test_render_process_table_contains_pid():
    row = ProcessRow(pid=1234, user="u", pr="20", ni=0, virt=1, res=1, shr=1,
                      state="R", cpu=1.0, mem=1.0, timep=1.0, cmd="x")
    lines = render_process_table([row], width=80, enabled=False)
    assert any("1234" in line for line in lines)


def test_core_rows_single_core():
    result = core_rows([42.0], per_row=4, enabled=False)
    assert len(result) == 1


def test_core_rows_five_cores_wraps_to_two_lines():
    result = core_rows([10.0] * 5, per_row=4, enabled=False)
    assert len(result) == 2
