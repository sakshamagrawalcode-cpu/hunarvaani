import pytest

from core import geo, sample_data
from core.dialogue.flow import AGE, EDUCATION, TRAVEL
from core.recommend import Profile, as_dict, reason_text, recommend
from core.search.seed import load_seed

DATA = sample_data.load()
SUNITA = Profile("7531", "26_35", "female", "upto_8th", "10km", "none", "own_work", "MH-PUN")


def codes(options):
    return [o.course.course_id for o in options]


def reason_codes(option):
    return [code for code, _ in option.reasons]


# --- the dataset --------------------------------------------------------------------------


def test_every_occupation_has_a_sample_profile_and_an_upskill_course():
    seed = {r.nco_code for r in load_seed()}
    assert set(DATA.occupations) == seed
    upskill = {c for course in DATA.courses if course.kind == "upskill" for c in course.nco_codes}
    assert upskill == seed


def test_rows_point_at_things_that_exist():
    sectors = set(DATA.sectors)
    course_sectors = sectors | {"rpl", "vishwakarma", "entrepreneurship"}
    for o in DATA.occupations.values():
        assert o.sector in sectors and set(o.near) <= set(DATA.occupations) - {o.nco_code}
        assert DATA.schemes[o.loan_scheme].kind in ("loan", "tools_and_loan")
    for c in DATA.courses:
        assert c.kind in ("upskill", "certificate", "startup")
        assert c.nco_codes == ("*",) or set(c.nco_codes) <= set(DATA.occupations), c.course_id
        assert c.sector in course_sectors and c.scheme in DATA.schemes
        assert c.min_education in EDUCATION.values() and 0 < c.min_age <= c.max_age
        assert c.hours > 0 and c.fee_inr >= 0 and 1 <= c.nsqf_level <= 8
    for centre in DATA.centres:
        assert centre.district_code in DATA.district_state
        assert set(centre.sectors) <= course_sectors and centre.distance_km > 0
    assert set(DATA.demand.values()) <= {"high", "low"}
    assert {d for d, _ in DATA.demand} <= set(DATA.district_state)


def test_every_course_is_taught_somewhere_and_every_district_has_all_centre_types():
    taught = {s for c in DATA.centres for s in c.sectors}
    assert {c.sector for c in DATA.courses} <= taught
    districts = {row["district_code"] for row in geo.table().values()}
    for d in districts:
        assert {c.type for c in DATA.centres if c.district_code == d} == {
            "block",
            "pmkk",
            "rseti",
            "iti",
        }


def test_the_interview_answers_are_all_understood():
    assert set(AGE.values()) == set(sample_data.AGE_RANGE)
    assert set(EDUCATION.values()) == set(sample_data.EDUCATION_ORDER)
    assert set(TRAVEL.values()) == set(sample_data.TRAVEL_KM)


# --- the recommender ----------------------------------------------------------------------


def test_sunita_tailor_who_wants_her_own_work_gets_three_close_options():
    options = recommend(SUNITA)
    assert [o.rank for o in options] == [1, 2, 3] and len(set(codes(options))) == 3
    assert options[0].course.kind == "startup" and options[0].loan_scheme == "PM-VISHWAKARMA"
    for o in options:
        assert not o.farther and o.centre.district_code == "MH-PUN"
        assert o.centre.distance_km <= 10 and "women_batch" in reason_codes(o)
    assert [o.score for o in options] == sorted((o.score for o in options), reverse=True)


def test_someone_who_wants_a_job_never_gets_business_training():
    p = Profile("7531", "26_35", "female", "upto_8th", "30km", "none", "job", "MH-PUN")
    options = recommend(p)
    assert options and all(o.course.kind != "startup" for o in options)
    assert options[0].course.placement


def test_physical_difficulty_drops_heavy_work_and_offers_a_near_trade():
    p = Profile("7112", "36_45", "male", "none", "30km", "some", "job", "MH-NAS")
    options = recommend(p)
    assert options and not any(o.course.heavy_work for o in options)
    assert "U7112" not in codes(options) and "U7131" in codes(options)  # painter, a near trade
    assert recommend(Profile("7112", "36_45", "male", "none", "30km", "none", "job", "MH-NAS"))[
        0
    ].course.course_id == ("U7112")


def test_age_and_education_limits():
    assert (
        recommend(Profile("7531", "under_18", "female", "10th", "30km", "none", "job", "MH-PUN"))
        == []
    )
    fifth = Profile("7422", "18_25", "male", "upto_5th", "30km", "none", "job", "MH-PUN")
    assert "U7422" not in codes(recommend(fifth))  # mobile repair needs 10th pass
    tenth = Profile("7422", "18_25", "male", "10th", "30km", "none", "job", "MH-PUN")
    assert "U7422" in codes(recommend(tenth))
    older = Profile("5131", "46_60", "male", "12th", "30km", "none", "job", "MH-PUN")
    assert "U5131" not in codes(recommend(older))  # waiter course is 18 to 35


def test_centres_beyond_the_travel_limit_come_last_and_say_so():
    p = Profile("9313", "18_25", "male", "none", "village", "none", "job", "UP-LKO")
    options = recommend(p)
    assert options
    flags = [o.farther for o in options]
    assert flags == sorted(flags)  # close ones first
    for o in options:
        if o.farther:
            assert o.centre.distance_km > 5 and "farther" in reason_codes(o)
        else:
            assert o.centre.distance_km <= 5


def test_hostel_callers_may_go_to_another_district_of_their_state():
    p = Profile("7223", "18_25", "male", "10th", "hostel", "none", "job", "MH-YAV")
    options = recommend(p)
    states = {DATA.district_state[o.centre.district_code] for o in options}
    assert states == {"Maharashtra"}
    for o in options:
        if o.centre.district_code != "MH-YAV":
            assert o.centre.hostel and "hostel" in reason_codes(o)


def test_no_pin_code_still_gives_options_without_a_centre():
    p = Profile("7314", "46_60", "male", "none", "10km", "none", "unsure", None)
    options = recommend(p)
    assert options and all(o.centre is None for o in options)
    assert all("centre_unknown" in reason_codes(o) for o in options)


def test_unknown_occupation_gives_nothing():
    assert recommend(Profile(None, "26_35", "male", "10th", "30km", "none", "job", "MH-PUN")) == []
    assert (
        recommend(Profile("0000", "26_35", "male", "10th", "30km", "none", "job", "MH-PUN")) == []
    )


def test_skill_gap_leaves_out_what_the_trade_already_knows():
    p = Profile("7411", "26_35", "male", "10th", "30km", "none", "job", "MH-NAG")
    [upskill] = [o for o in recommend(p) if o.course.course_id == "U7411"]
    assert "fault finding" in upskill.course.skills and "fault finding" not in upskill.gap
    assert len(upskill.gap) == len(upskill.course.skills) - 1
    [certificate] = [o for o in recommend(p) if o.course.kind == "certificate"]
    assert certificate.gap == () and "certificate" in reason_codes(certificate)


@pytest.mark.parametrize("lean", ["job", "own_work", "unsure"])
@pytest.mark.parametrize("travel", list(sample_data.TRAVEL_KM))
def test_every_occupation_gets_an_option_in_every_district(lean, travel):
    districts = sorted(DATA.district_state)
    for code in DATA.occupations:
        for d in districts:
            options = recommend(Profile(code, "26_35", "male", "10th", travel, "none", lean, d))
            assert options, (code, d)
            assert all(0 <= o.score <= 1.03 for o in options)


def test_answers_become_a_profile():
    answers = {
        "q_age": "26_35",
        "q_gender": "not_said",
        "q_education": "skipped",
        "q_travel": "10km",
        "q_physical": "none",
        "q_lean": "own_work",
        "q_district": "unknown",
        "trades": "7531",
    }
    p = Profile.from_answers(answers)
    assert p == Profile("7531", "26_35", None, None, "10km", "none", "own_work", None)
    assert Profile.from_answers({**answers, "occupation": "7533"}).occupation == "7533"


def test_options_as_json_are_labelled_sample_and_readable():
    first = as_dict(recommend(SUNITA)[0])
    assert first["sample"] is True and first["rank"] == 1
    assert first["loan"] == "PM Vishwakarma" and first["centre"].endswith("Pune")
    assert any("Women-only" in r for r in first["reasons"])
    assert reason_text("near_you", {"km": 8, "limit": 10}) == (
        "Centre about 8 km away (you can go up to 10 km)"
    )
