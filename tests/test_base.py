from wptemps.metrics.base import Metrics, format_lines


def test_format_lines_all_values():
    m = Metrics(
        cpu_temp=55.4, gpu_temp=48.5, cpu_load=12.0,
        ram_used_gb=11.2, ram_total_gb=17.2, battery_pct=87.0, fan_rpm=None,
    )
    lines = format_lines(m)
    assert lines[0] == "CPU  55°C  12%"
    assert lines[1] == "GPU  48°C"
    assert lines[2] == "RAM  11.2 / 17.2 GB"
    assert lines[3] == "BAT  87%"
    assert all("FAN" not in l for l in lines)  # pas de ventilo -> ligne omise


def test_format_lines_handles_missing():
    lines = format_lines(Metrics())
    assert lines[0] == "CPU  N/A  N/A"
    assert lines[1] == "GPU  N/A"
    assert lines[2] == "RAM  N/A"
    assert lines[3] == "BAT  N/A"


def test_format_lines_includes_fan_when_present():
    lines = format_lines(Metrics(fan_rpm=2400.0))
    assert any(l == "FAN  2400 rpm" for l in lines)
