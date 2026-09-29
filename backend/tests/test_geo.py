from core.geo import UNKNOWN, district_for_pin, district_name, valid_pin


def test_valid_pin_is_six_digits_not_starting_with_zero():
    assert valid_pin("411001") and valid_pin("800001")
    assert not any(valid_pin(x) for x in ("", "41100", "4110011", "011001", "41100a", "٤١١٠٠١"))


def test_district_from_the_first_three_digits_in_each_language():
    row = district_for_pin("411045")
    assert row["district_code"] == "MH-PUN" and row["state"] == "Maharashtra"
    assert district_name(row, "en-IN") == "Pune"
    assert district_name(district_for_pin("440010"), "mr-IN") == "नागपूर"
    assert district_name(district_for_pin("226001"), "hi-IN") == "लखनऊ"


def test_pin_outside_thetable_or_invalid_gives_nothing():
    assert district_for_pin("999999") is None and district_for_pin("12") is None
    assert UNKNOWN == "unknown"


def test_everytable_row_is_complete_and_codes_agree():
    from core.geo import table

    names = {}
    for prefix, r in table().items():
        assert len(prefix) == 3 and prefix.isdigit()
        assert all(r[k] for k in ("state", "district_code", "district_en", "district_hi"))
        assert names.setdefault(r["district_code"], r["district_en"]) == r["district_en"]
