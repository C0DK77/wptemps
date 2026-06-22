from wptemps.sysinfo import (
    MachineInfo, disk_gb, machine_info, parse_model_name, parse_os_version, parse_soc,
)

SOC = {"chip_name": "Apple M3", "pcpu_cores": 4, "ecpu_cores": 4,
       "gpu_cores": 8, "memory_gb": 16, "mac_model": "Mac15,12"}
_GB = 1024 ** 3


def test_parse_soc_full():
    d = parse_soc(SOC)
    assert d["chip"] == "Apple M3"
    assert d["cpu_cores"] == 8 and d["cpu_p"] == 4 and d["cpu_e"] == 4
    assert d["gpu_cores"] == 8 and d["ram_gb"] == 16


def test_parse_soc_empty():
    d = parse_soc({})
    assert d["chip"] is None and d["cpu_cores"] is None and d["gpu_cores"] is None


def test_parse_os_version():
    assert parse_os_version("15.6.1\n") == "15.6.1"
    assert parse_os_version("") is None


def test_parse_model_name():
    out = "Hardware:\n\n    Model Name: MacBook Air\n    Model Identifier: Mac15,12\n"
    assert parse_model_name(out) == "MacBook Air"
    assert parse_model_name("rien") is None


def test_disk_gb():
    assert disk_gb(228 * _GB, 24 * _GB) == (228.0, 24.0)


def test_machine_info_assembles_from_readers():
    mi = machine_info(
        soc_reader=lambda: SOC,
        os_reader=lambda: "15.6.1\n",
        model_reader=lambda: "Model Name: MacBook Air\n",
        disk_reader=lambda: (228 * _GB, 24 * _GB),
    )
    assert mi.os_version == "15.6.1"
    assert mi.model_name == "MacBook Air"
    assert mi.chip == "Apple M3" and mi.cpu_cores == 8 and mi.gpu_cores == 8
    assert mi.ram_gb == 16
    assert mi.disk_total_gb == 228.0 and mi.disk_free_gb == 24.0


def test_machine_info_survives_failing_reader():
    def boom():
        raise RuntimeError("macmon HS")
    mi = machine_info(
        soc_reader=boom,
        os_reader=lambda: "15.6.1\n",
        model_reader=lambda: "Model Name: MacBook Air\n",
        disk_reader=lambda: (228 * _GB, 24 * _GB),
    )
    assert mi.chip is None and mi.cpu_cores is None   # soc a echoue
    assert mi.os_version == "15.6.1"                  # le reste tient
    assert mi.model_name == "MacBook Air"
