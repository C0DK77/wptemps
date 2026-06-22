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


def test_format_lines_show_power_appends_watts():
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, gpu_temp=48.0,
                cpu_power=4.2, gpu_power=0.1)
    lines = format_lines(m, show_power=True)
    assert lines[0] == "CPU  55°C  10%  4.2W"
    assert lines[1] == "GPU  48°C  0.1W"


def test_format_lines_default_has_no_watts():
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, cpu_power=4.2)
    assert format_lines(m)[0] == "CPU  55°C  10%"   # defaut inchange


def test_format_lines_show_power_omits_missing_watt():
    m = Metrics(cpu_temp=55.0, cpu_load=10.0, cpu_power=None)
    assert format_lines(m, show_power=True)[0] == "CPU  55°C  10%"
