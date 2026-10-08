from backend.app.services.bmi import calc_bmi


def test_bmi_normal():
    assert calc_bmi(70, 175) == 22.9


def test_bmi_bad_height():
    assert calc_bmi(70, 0) is None
