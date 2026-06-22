from wptemps.extras import (
    NetRateMeter, apply_extras, parse_boottime, parse_net_counters, uptime_seconds,
)
from wptemps.metrics.base import Metrics

NETSTAT = (
    "Name  Mtu   Network       Address            Ipkts Ierrs     Ibytes    Opkts Oerrs     Obytes  Coll\n"
    "lo0   16384 <Link#1>                           100     0       8000      100     0       8000     0\n"
    "en0   1500  <Link#11>     a4:83:e7:00:00:00   2000     0    1000000     1500     0     500000     0\n"
    "en0   1500  192.168.1     mymac               2000     0    1000000     1500     0     500000     0\n"
)


def test_parse_boottime():
    assert parse_boottime("{ sec = 1700000000, usec = 0 } Tue ...") == 1700000000
    assert parse_boottime("rien") is None


def test_uptime_seconds():
    up = uptime_seconds(boottime_reader=lambda: "{ sec = 100, usec = 0 }", now=lambda: 1000.0)
    assert up == 900.0


def test_uptime_seconds_survives_failure():
    def boom():
        raise RuntimeError("sysctl HS")
    assert uptime_seconds(boottime_reader=boom, now=lambda: 1.0) is None


def test_parse_net_counters_sums_link_rows_skips_lo():
    assert parse_net_counters(NETSTAT) == (1000000, 500000)


def test_net_rate_meter_first_sample_is_zero():
    meter = NetRateMeter()
    assert meter.sample(1000, 2000, now=10.0) == (0.0, 0.0)


def test_net_rate_meter_computes_kbps():
    meter = NetRateMeter()
    meter.sample(0, 0, now=0.0)
    # +2048 octets in / +1024 out sur 2 s -> 1.0 / 0.5 KB/s
    down, up = meter.sample(2048, 1024, now=2.0)
    assert round(down, 3) == 1.0
    assert round(up, 3) == 0.5


def test_net_rate_meter_zero_when_no_time_advance():
    meter = NetRateMeter()
    meter.sample(0, 0, now=5.0)
    assert meter.sample(9999, 9999, now=5.0) == (0.0, 0.0)


def test_apply_extras_fills_fields():
    meter = NetRateMeter()
    m = apply_extras(Metrics(), meter,
                     net_reader=lambda: (1000, 2000),
                     uptime_fn=lambda: 3600.0, now=lambda: 0.0)
    assert m.net_down_kbps == 0.0 and m.net_up_kbps == 0.0   # 1er echantillon
    assert m.uptime_seconds == 3600.0


def test_apply_extras_survives_failing_reader():
    def boom():
        raise RuntimeError("netstat HS")
    m = apply_extras(Metrics(), NetRateMeter(),
                     net_reader=boom, uptime_fn=lambda: 5.0, now=lambda: 0.0)
    assert m.net_down_kbps is None     # reseau a echoue
    assert m.uptime_seconds == 5.0     # uptime tient
