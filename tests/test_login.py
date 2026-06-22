from wptemps import login


def test_available_false_from_source():
    # non empaquete (sys.frozen absent) -> indisponible
    assert login.available() is False


def test_is_enabled_safe_when_unavailable():
    # ne doit jamais lever, renvoie un bool
    assert login.is_enabled() in (True, False)


def test_set_enabled_safe_when_unavailable():
    # depuis les sources : echoue proprement, renvoie False, sans exception
    assert login.set_enabled(True) is False
    assert login.set_enabled(False) is False
