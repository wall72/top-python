from top_python.collectors import ProcessCollector, cpu_breakdown, memory_snapshot, LoadAverageTracker


def test_process_collector_returns_rows_and_states():
    collector = ProcessCollector()
    rows, states = collector.collect()
    assert len(rows) > 0
    assert sum(states.values()) == len(rows)
    assert all(hasattr(r, "pid") for r in rows)


def test_cpu_breakdown_has_expected_keys():
    result = cpu_breakdown()
    assert set(result.keys()) == {"us", "sy", "ni", "id", "wa", "hi", "si", "st"}


def test_memory_snapshot_has_expected_keys():
    result = memory_snapshot()
    assert result["mem_total"] >= result["mem_used"]


def test_load_average_tracker_moves_toward_target():
    tracker = LoadAverageTracker(cpu_count=4)
    first = tracker.update(cpu_used=50.0, dt=60.0)
    second = tracker.update(cpu_used=50.0, dt=60.0)
    assert second[0] > first[0]
