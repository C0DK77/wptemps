from wptemps.metrics.macos import metrics_from_macmon, parse_battery_pct

SAMPLE = {
    "cpu_usage_pct": 0.03833765536546707,
    "memory": {"ram_total": 17179869184, "ram_usage": 11243503616,
               "swap_total": 2147483648, "swap_usage": 1085931520},
    "temp": {"cpu_temp_avg": 55.41343688964844, "gpu_temp_avg": 48.45880126953125},
}


def test_metrics_from_macmon_extracts_fields():
    d = metrics_from_macmon(SAMPLE)
    assert d["cpu_temp"] == 55.41343688964844
    assert d["gpu_temp"] == 48.45880126953125
    assert d["cpu_load"] == 3.8          # fraction -> pourcentage, arrondi 1 decimale
    assert d["ram_total_gb"] == 16.0     # 17179869184 / 1024^3
    assert d["ram_used_gb"] == 10.5      # 11243503616 / 1024^3, arrondi


def test_metrics_from_macmon_tolerates_missing_keys():
    d = metrics_from_macmon({})
    assert d["cpu_temp"] is None
    assert d["ram_total_gb"] is None
    assert d["cpu_load"] is None


def test_parse_battery_pct():
    out = (" -InternalBattery-0 (id=12345)\t87%; discharging; 4:32 remaining present: true")
    assert parse_battery_pct(out) == 87.0


def test_parse_battery_pct_absent():
    assert parse_battery_pct("Now drawing from 'AC Power'") is None
