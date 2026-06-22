import json

from wptemps.metrics.macos import read_metrics

SAMPLE_JSON = json.dumps({
    "cpu_usage_pct": 0.05,
    "memory": {"ram_total": 17179869184, "ram_usage": 8589934592},
    "temp": {"cpu_temp_avg": 60.0, "gpu_temp_avg": 50.0},
})
BATT = " -InternalBattery-0 (id=1)\t91%; discharging; 3:00 remaining"


def test_read_metrics_combines_sources():
    m = read_metrics(sampler=lambda: SAMPLE_JSON, battery_reader=lambda: BATT)
    assert m.cpu_temp == 60.0
    assert m.gpu_temp == 50.0
    assert m.cpu_load == 5.0
    assert m.ram_total_gb == 16.0
    assert m.battery_pct == 91.0


def test_read_metrics_survives_sampler_failure():
    def boom():
        raise RuntimeError("macmon absent")
    m = read_metrics(sampler=boom, battery_reader=lambda: BATT)
    assert m.cpu_temp is None          # macmon a echoue -> None
    assert m.battery_pct == 91.0       # batterie toujours lue


def test_read_metrics_survives_battery_failure():
    def boom():
        raise RuntimeError("pmset absent")
    m = read_metrics(sampler=lambda: SAMPLE_JSON, battery_reader=boom)
    assert m.cpu_temp == 60.0
    assert m.battery_pct is None
