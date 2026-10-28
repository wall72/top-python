from top_python.models import ProcessRow, ProcCacheEntry


def test_process_row_field_access():
    row = ProcessRow(pid=1, user="root", pr="20", ni=0, virt=1.0, res=2.0,
                      shr=0.5, state="R", cpu=10.0, mem=5.0, timep=1.5, cmd="init")
    assert row.pid == 1
    assert row.cmd == "init"


def test_proc_cache_entry_defaults():
    entry = ProcCacheEntry(proc=None)
    assert entry.primed is False
    assert entry.user == "?"
    assert entry.cmdline_full is None
