from wptemps.metrics.macos import _macmon_path


def test_macmon_path_source_mode_returns_plain_name():
    assert _macmon_path(frozen=False) == "macmon"


def test_macmon_path_bundle_returns_embedded_when_present():
    p = _macmon_path(
        frozen=True,
        executable="/Apps/wptemps.app/Contents/MacOS/wptemps",
        exists=lambda path: True,
    )
    assert p == "/Apps/wptemps.app/Contents/Resources/macmon"


def test_macmon_path_bundle_falls_back_when_absent():
    p = _macmon_path(
        frozen=True,
        executable="/Apps/wptemps.app/Contents/MacOS/wptemps",
        exists=lambda path: False,
    )
    assert p == "macmon"
