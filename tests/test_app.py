from top_python.app import SystemMonitor


def test_handle_key_c_sets_cpu_sort():
    monitor = SystemMonitor()
    monitor.sort_key = "mem"
    monitor.handle_key("c")
    assert monitor.sort_key == "cpu"
    assert monitor.sort_reverse is True


def test_handle_key_q_stops_running():
    monitor = SystemMonitor()
    monitor.handle_key("q")
    assert monitor.running is False


def test_handle_key_r_toggles_reverse():
    monitor = SystemMonitor()
    before = monitor.sort_reverse
    monitor.handle_key("r")
    assert monitor.sort_reverse is not before
