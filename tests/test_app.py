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


def test_handle_key_plus_increases_interval():
    monitor = SystemMonitor()
    monitor.update_interval = 1.0
    monitor.handle_key("+")
    assert monitor.update_interval == 1.5


def test_handle_key_minus_decreases_interval():
    monitor = SystemMonitor()
    monitor.update_interval = 1.0
    monitor.handle_key("-")
    assert monitor.update_interval == 0.5


def test_handle_key_minus_does_not_go_below_half_second():
    monitor = SystemMonitor()
    monitor.update_interval = 0.5
    monitor.handle_key("-")
    assert monitor.update_interval == 0.5
