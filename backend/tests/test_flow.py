from core.dialogue.flow import MAX_STORY_ATTEMPTS, Ask, Effect, Hangup, Interview, Offer, Record


def kinds(effects):
    return [e.kind for e in effects]


def run(iv, keys):
    """Press keys in order; return (last action, all effects)."""
    effects = []
    action = iv.start()
    for k in keys:
        if k == "T":
            action, eff = iv.on_timeout()
        elif k == "P":  # a valid PIN code entry
            action, eff = iv.on_digits("411001")
        else:
            action, eff = iv.on_key(k)
        effects += eff
    return action, effects


def test_happy_path_with_recording():
    iv = Interview()
    action, effects = run(iv, ["1", "1", "1", "1", "2", "3", "1", "4", "2", "2"])
    assert action.step == "q_pin"
    action, more = iv.on_digits("411001")
    effects += more
    action, more = iv.on_key("1")
    effects += more
    assert isinstance(action, Record) and action.prompts == ("P12",)
    answers = {e.data["step"]: e.data["value"] for e in effects if e.kind == "answer"}
    assert answers == {
        "q_age": "26_35",
        "q_gender": "female",
        "q_education": "10th",
        "q_travel": "10km",
        "q_physical": "some",
        "q_pin": "411001",
        "q_lean": "job",
    }
    consents = [(e.data["kind"], e.data["granted"]) for e in effects if e.kind == "consent"]
    assert consents == [("recording", True), ("share", True), ("research", False)]

    action, effects = iv.on_recording("/rec/a.wav", 12.34, understood=False)
    assert kinds(effects) == ["story_recorded"] and effects[0].data["seconds"] == 12.3
    assert action.prompts == ("P14",)
    action, effects = iv.on_key("2")
    assert effects[0].data == {"step": "trades", "key": "2", "value": "7531"}
    assert action == Offer() and iv.state == "offer"
    assert (iv.education, iv.occupation) == ("10th", "7531")


def test_language_menu_is_skipped_with_one_language():
    iv = Interview()
    assert iv.start().prompts == ("P01",)
    action = iv.on_key("1")[0]
    assert action.prompts == ("P03",) and iv.language == "hi-IN"
    action, _ = iv.on_key("1")
    assert action.prompts == ("P06",)


def test_the_call_starts_with_the_language_menu_then_greets_in_that_language():
    iv = Interview(languages=["hi-IN", "en-IN", "mr-IN"])
    action = iv.start()
    assert iv.state == "language"
    assert action.prompts == ("P05@hi-IN", "P05@en-IN", "P05@mr-IN")
    assert action.valid == "123" + "90"
    action, effects = iv.on_key("3")
    assert effects[0].data == {"code": "mr-IN"} and iv.language == "mr-IN"
    assert action.prompts == ("P01",) and iv.state == "opening"
    action, _ = iv.on_key("1")
    assert action.prompts == ("P03",) and iv.state == "safe_to_talk"


def test_language_keys_stay_fixed_when_one_is_left_out():
    iv = Interview(languages=["hi-IN", "mr-IN"])
    action = iv.start()
    assert action.prompts == ("P05@hi-IN", "P05@mr-IN") and action.valid == "13" + "90"
    action, _ = iv.on_key("2")
    assert iv.state == "language" and action.prompts == ("P05@hi-IN", "P05@mr-IN")
    iv.on_key("3")
    assert iv.language == "mr-IN"


def test_no_language_choice_plays_the_menu_again_and_again():
    iv = Interview(languages=["hi-IN", "en-IN"])
    iv.start()
    for _ in range(5):
        action, effects = iv.on_timeout()
        assert action.prompts == ("P05@hi-IN", "P05@en-IN") and effects == []
        assert iv.state == "language"
    action, _ = iv.on_key("2")
    assert iv.language == "en-IN" and action.prompts == ("P01",)


def test_wrong_key_and_no_key_get_different_apologies():
    iv = Interview()
    run(iv, ["1"])
    action, _ = iv.on_key("7")
    assert action.prompts == ("P29", "P03")
    iv2 = Interview()
    run(iv2, ["1"])
    action, _ = iv2.on_timeout()
    assert action.prompts == ("P16", "P03")


def test_no_to_recording_means_keypad_only_and_no_story():
    iv = Interview()
    action, effects = run(iv, ["1", "1", "2", "1", "1", "3", "1", "3", "3", "1", "P", "2"])
    assert "keypad_only" in kinds(effects) and iv.keypad_only
    assert isinstance(action, Ask) and action.prompts == ("P14",)


def test_no_answer_repeats_the_question_and_never_skips():
    iv = Interview()
    run(iv, ["1", "1", "1", "1", "1", "3", "1"])
    assert iv.state == "q_education"
    for _ in range(6):
        action, effects = iv.on_timeout()
        assert action.prompts == ("P16", "P09") and effects == []
    action, _ = iv.on_key("8")
    assert action.prompts == ("P29", "P09") and iv.state == "q_education"
    action, effects = iv.on_key("4")
    assert action.prompts == ("P10",) and effects[0].data["value"] == "10th"


def test_wrong_key_counts_like_a_timeout():
    iv = Interview()
    run(iv, ["1", "1", "1", "1", "1"])
    action, _ = iv.on_key("8")
    assert action.prompts == ("P29", "P25")


def test_age_gender_and_physical_questions_come_around_education():
    iv = Interview()
    action, _ = run(iv, ["1", "1", "1", "1", "1"])
    assert action.prompts == ("P28", "P25") and action.valid == "123456" + "90"
    action, _ = iv.on_key("6")
    assert action.prompts == ("P26",) and action.valid == "1234" + "90"
    action, _ = iv.on_key("4")
    assert action.prompts == ("P09",)
    iv.on_key("7")
    action, _ = iv.on_key("5")
    assert action.prompts == ("P27",) and action.valid == "12" + "90"
    action, effects = iv.on_key("1")
    assert action.prompts == ("P31",) and action.digits == 6 and "9" in action.valid
    assert effects[0].data == {"step": "q_physical", "key": "1", "value": "none"}


def test_pin_code_is_asked_again_until_six_digits_and_can_be_skipped_with_star():
    def at_pin():
        iv = Interview()
        run(iv, ["1", "1", "1", "1", "1", "3", "1", "4", "2", "2"])
        assert iv.state == "q_pin"
        return iv

    iv = at_pin()
    for entry in ("0123", "012345", "", "41100"):  # too short or a leading zero: asked again
        action, effects = iv.on_digits(entry)
        assert action.prompts == ("P32", "P31") and effects == [] and iv.state == "q_pin"
    action, effects = iv.on_digits("411001")
    assert action.prompts == ("P11",) and effects[0].data["value"] == "411001"

    iv = at_pin()
    action, effects = iv.on_digits("*")  # the caller's own choice to skip
    assert action.prompts == ("P11",) and effects == [Effect("skipped", {"step": "q_pin"})]

    iv = at_pin()
    for _ in range(3):  # silence never skips the question
        action, effects = iv.on_timeout()
        assert action.prompts == ("P16", "P31") and effects == []

    iv = at_pin()  # 9 and 0 are digits here: no deletion, no human flag
    action, effects = iv.on_key("9")
    assert iv.state == "q_pin" and kinds(effects) == [] and action.prompts == ("P32", "P31")


def test_unanswered_consent_is_asked_again_not_taken_as_no():
    iv = Interview()
    run(iv, ["1", "1"])
    for _ in range(3):
        action, effects = iv.on_timeout()
        assert action.prompts == ("P16", "P06") and effects == []
    assert not iv.keypad_only and iv.state == "consent_recording"


def test_nine_anywhere_deletes_and_blocks():
    for presses in (["9"], ["1", "9"], ["1", "1", "1", "1", "1", "9"]):
        iv = Interview()
        action, effects = run(iv, presses)
        assert action == Hangup(("P18",)) and kinds(effects)[-1] == "delete_and_block"


def test_zero_flags_a_human_and_repeats_the_question():
    iv = Interview()
    run(iv, ["1"])
    action, effects = iv.on_key("0")
    assert action.prompts == ("P19", "P03")
    assert effects[0].kind == "human_flag" and effects[0].data == {"step": "safe_to_talk"}
    assert iv.state == "safe_to_talk"


def test_silent_opening_asks_can_you_hear_us_and_never_hangs_up():
    iv = Interview()
    iv.start()
    action, _ = iv.on_timeout()
    assert action.prompts == ("P02",)
    for _ in range(4):
        action, effects = iv.on_timeout()
        assert action.prompts == ("P16", "P02") and effects == []
    action, _ = iv.on_key("4")
    assert action.prompts == ("P29", "P02")
    action, _ = iv.on_key("1")
    assert action.prompts == ("P03",)


def test_silent_opening_then_nine_blocks():
    iv = Interview()
    action, effects = run(iv, ["T", "9"])
    assert action == Hangup(("P18",)) and kinds(effects) == ["delete_and_block"]


def test_not_now_schedules_a_callback_tomorrow():
    iv = Interview()
    action, effects = run(iv, ["1", "2"])
    assert action == Hangup(("P04",)) and kinds(effects) == ["callback_tomorrow"]


def test_state_survives_serialisation():
    iv = Interview(languages=["hi-IN", "en-IN"])
    run(iv, ["1", "1", "2"])
    copy = Interview.from_dict(iv.to_dict())
    assert copy == iv
    assert copy.on_key("1")[0] == iv.on_key("1")[0]


def test_no_speech_asks_again_then_offers_the_trade_list():
    iv = Interview()
    run(iv, ["1", "1", "1", "1", "1", "3", "1", "4", "2", "1", "P", "1"])
    for _ in range(MAX_STORY_ATTEMPTS - 1):
        action, effects = iv.on_recording(None, 0.0)
        assert kinds(effects) == ["story_empty"]
        assert isinstance(action, Record) and action.prompts == ("P22", "P23")
    action, effects = iv.on_recording(None, 0.0)
    assert kinds(effects) == ["story_empty"] and action.prompts == ("P22", "P14")


def _story(iv):
    run(iv, ["1", "1", "1", "1", "1", "3", "1", "4", "2", "1", "P", "1"])


def test_confident_story_says_what_we_heard_and_reads_back_two_occupations():
    iv = Interview()
    _story(iv)
    action, effects = iv.on_recording(
        "/r.wav",
        5,
        ["7531", "7411"],
        readback=["DYN:bb"],
        details={"top1": "7531"},
        heard=["DYN:aa"],
    )
    assert action.step == "readback" and action.prompts == ("DYN:aa", "DYN:bb")
    assert effects[0].data["top1"] == "7531"
    action, effects = iv.on_key("2")
    assert action == Offer() and iv.occupation == "7411"
    assert effects[0].data == {"key": "2", "confirmed": "7411", "candidates": ["7531", "7411"]}
    assert effects[1].data == {"step": "occupation", "key": "2", "value": "7411"}


def test_three_occupations_are_offered_and_4_means_none():
    iv = Interview()
    _story(iv)
    action, _ = iv.on_recording(
        "/r.wav", 5, ["7531", "7411", "7231"], readback=["DYN:bb"], heard=["DYN:aa"]
    )
    assert action.valid == "1234" + "90"
    action, _ = iv.on_key("3")
    assert action == Offer() and iv.occupation == "7231"


def test_none_of_these_lets_the_caller_tell_it_again():
    iv = Interview()
    _story(iv)
    iv.on_recording("/r.wav", 5, ["7531", "7411"], readback=["DYN:bb"], heard=["DYN:aa"])
    action, _ = iv.on_key("4")  # only two options: 3 means none, 4 is a wrong key
    assert action.prompts == ("P29", "DYN:aa", "DYN:bb")
    action, effects = iv.on_key("3")
    assert isinstance(action, Record) and action.prompts == ("P23",)
    assert effects[0].data == {"key": "3", "confirmed": None, "candidates": ["7531", "7411"]}
    for _ in range(MAX_STORY_ATTEMPTS - 1):
        iv.on_recording("/r2.wav", 5, ["7531"], readback=["DYN:dd"], heard=["DYN:cc"])
        action, _ = iv.on_key("2")
    assert action.prompts == ("P14",)


def test_read_back_timeouts_keep_repeating_the_read_back():
    iv = Interview()
    _story(iv)
    iv.on_recording("/r.wav", 5, ["7531", "7411"], readback=["DYN:bb"], heard=["DYN:aa"])
    for _ in range(3):
        action, effects = iv.on_timeout()
        assert action.prompts == ("P16", "DYN:aa", "DYN:bb") and effects == []
    action, _ = iv.on_key("1")
    assert action == Offer() and iv.occupation == "7531"


def test_unclear_story_says_what_we_heard_and_asks_for_more_detail():
    iv = Interview()
    _story(iv)
    action, effects = iv.on_recording("/r.wav", 5, [], None, {"top1": "5142"}, heard=["DYN:aa"])
    assert kinds(effects) == ["story_recorded"]
    assert isinstance(action, Record) and action.prompts == ("DYN:aa", "P24", "P23")
    action, _ = iv.on_recording("/r2.wav", 5, [], None, heard=["DYN:cc"])
    assert action.prompts == ("DYN:cc", "P24", "P23")
    action, _ = iv.on_recording("/r3.wav", 5, [], None, heard=["DYN:ee"])
    assert action.prompts == ("DYN:ee", "P24", "P14")


def test_second_story_can_be_confirmed():
    iv = Interview()
    _story(iv)
    iv.on_recording("/r.wav", 5, [], None, heard=["DYN:aa"])
    action, _ = iv.on_recording("/r2.wav", 5, ["7231", "7233"], readback=["DYN:dd"])
    assert action.step == "readback"
    action, _ = iv.on_key("1")
    assert action == Offer() and iv.occupation == "7231"


def test_slow_or_failed_processing_goes_straight_to_the_trade_list():
    iv = Interview()
    _story(iv)
    action, _ = iv.on_recording("/r.wav", 5, understood=False)
    assert action.prompts == ("P14",)


def test_trade_list_is_repeated_until_the_caller_picks_one():
    iv = Interview()
    run(iv, ["1", "1", "2", "1", "1", "3", "1", "3", "3", "1", "P", "2"])
    for _ in range(3):
        action, _ = iv.on_timeout()
        assert action.prompts == ("P16", "P14")
    action, _ = iv.on_key("5")
    assert action == Offer() and iv.occupation == "7422"


def at_options(courses=("U7531", "R7531", "V0001")):
    iv = Interview()
    run(iv, ["1", "1", "2", "1", "1", "3", "1", "3", "3", "1", "P", "2"])
    action, _ = iv.on_key("2")  # tailor from the trade list
    assert action == Offer() and iv.state == "offer"
    assert iv.answers["trades"] == "7531" and iv.answers["q_pin"] == "411001"
    details = [{"rank": i, "course_id": c} for i, c in enumerate(courses, 1)]
    action, effects = iv.on_options(list(courses), ["DYN:abc"], details)
    return iv, action, effects


def test_options_are_offered_after_the_occupation_and_the_choice_is_saved():
    iv, action, effects = at_options()
    assert effects == [
        Effect(
            "recommendations",
            {
                "options": [{"rank": i, "course_id": c} for i, c in enumerate(iv.options, 1)],
                "spoken": True,
            },
        )
    ]
    assert action == Ask("options", ("DYN:abc",), "1234" + "90", 8)
    assert iv.on_key("7")[0].prompts == ("P29", "DYN:abc")  # not an option: asked again
    assert iv.on_timeout()[0].prompts == ("P16", "DYN:abc")  # silence: asked again
    action, effects = iv.on_key("2")
    assert action == Hangup(("P33",)) and iv.state == "ended"
    assert effects[0] == Effect("interest", {"rank": 2, "course_id": "R7531"})
    assert effects[1].data == {"step": "interest", "key": "2", "value": "R7531"}


def test_none_of_the_options_is_saved_too():
    iv, _, _ = at_options(("U7531", "R7531"))
    assert iv._action().valid == "123" + "90"
    action, effects = iv.on_key("3")
    assert action == Hangup(("P33",))
    assert effects[0].data == {"rank": None, "course_id": None}
    assert iv.answers["interest"] == "none"


def test_no_options_or_no_voice_ends_with_the_summary():
    iv = Interview()
    run(iv, ["1", "1", "2", "1", "1", "3", "1", "3", "3", "1", "P", "2", "2"])
    assert iv.on_options([], [], []) == (Hangup(("P15",)), [])
    iv = Interview()
    run(iv, ["1", "1", "2", "1", "1", "3", "1", "3", "3", "1", "P", "2", "2"])
    action, effects = iv.on_options(["U7531"], [], [{"rank": 1}])  # voice failed
    assert action == Hangup(("P15",)) and effects[0].data["spoken"] is False


def test_nine_still_deletes_at_the_options():
    iv, _, _ = at_options()
    action, effects = iv.on_key("9")
    assert action == Hangup(("P18",)) and kinds(effects) == ["delete_and_block"]


def at_review():
    iv = Interview(review=True, closing=True)
    run(iv, ["1", "1", "1", "1", "1", "3", "1", "4", "2", "1", "P", "2"])
    assert iv.state == "review"
    return iv


def test_the_caller_hears_every_saved_answer_and_can_go_on():
    iv = at_review()
    action = iv._action()
    assert action.prompts == (
        "P35",
        "V_q_age_26_35",
        "V_q_gender_female",
        "V_q_education_10th",
        "V_q_travel_10km",
        "V_q_physical_none",
        "V_pin",
        "D4",
        "D1",
        "D1",
        "D0",
        "D0",
        "D1",
        "V_q_lean_own_work",
        "P36",
    )
    assert action.valid == "12" + "90"
    action, effects = iv.on_key("1")
    assert isinstance(action, Record) and effects == [Effect("review", {"ok": True})]


def test_the_caller_can_change_one_answer_and_hears_the_review_again():
    iv = at_review()
    action, _ = iv.on_key("2")
    assert action.prompts == ("P37",) and action.valid == "1234567" + "90"
    action, effects = iv.on_key("3")  # education
    assert action.prompts == ("P09",) and effects[0].data == {"change": "q_education"}
    action, effects = iv.on_key("7")  # graduate
    assert effects[0].data["value"] == "graduate" and iv.education == "graduate"
    assert iv.state == "review" and "V_q_education_graduate" in action.prompts
    iv.on_key("2")
    action, _ = iv.on_key("1")  # age: no "why we ask" this time
    assert action.prompts == ("P25",)
    iv.on_key("6")
    iv.on_key("2")
    action, _ = iv.on_key("6")  # the PIN code
    assert action.prompts == ("P31",)
    action, _ = iv.on_digits("*")
    assert iv.state == "review" and "V_pin_none" in action.prompts and "V_pin" not in action.prompts
    iv.on_key("1")
    assert iv.state == "story"


def test_the_call_ends_with_the_reference_number_and_the_documents():
    iv = at_review()
    iv.on_key("1")
    iv.on_recording(None, 0)
    iv.on_recording(None, 0)
    iv.on_recording(None, 0)  # no speech three times: the trade list
    action, _ = iv.on_key("2")
    assert action == Offer()
    action, _ = iv.on_options(["U7531"], ["DYN:x"], [{"rank": 1}])
    action, _ = iv.on_key("1")
    assert action == Hangup(("P33", "REF", "P39"))
    iv = at_review()
    iv.on_key("1")
    for _ in range(3):
        iv.on_recording(None, 0)
    iv.on_key("2")
    assert iv.on_options([], [], [])[0] == Hangup(("P15", "REF", "P39"))


def test_an_options_number_plays_its_details_then_choose_or_go_back():
    iv = Interview(closing=True)
    run(iv, ["1", "1", "2", "1", "1", "3", "1", "3", "3", "1", "P", "2", "2"])
    details = [{"rank": i} for i in (1, 2, 3)]
    action, _ = iv.on_options(
        ["U1", "R1", "V1"], ["DYN:all"], details, [["DYN:d1"], [], ["DYN:d3"]]
    )
    action, effects = iv.on_key("3")
    assert action.prompts == ("DYN:d3", "P41") and action.valid == "12" + "90"
    assert effects == [Effect("option_heard", {"rank": 3})]
    action, _ = iv.on_key("2")  # back to the options
    assert action.prompts == ("DYN:all",) and iv.state == "options"
    action, effects = iv.on_key("2")  # no details for option 2: chosen at once
    assert action == Hangup(("P33", "REF", "P39"))
    assert effects[0].data == {"rank": 2, "course_id": "R1"}


def test_choosing_after_the_details_saves_that_option():
    iv = Interview()
    run(iv, ["1", "1", "2", "1", "1", "3", "1", "3", "3", "1", "P", "2", "2"])
    iv.on_options(["U1", "R1"], ["DYN:all"], [{}, {}], [["DYN:d1"], ["DYN:d2"]])
    iv.on_key("1")
    assert iv.on_timeout()[0].prompts == ("P16", "DYN:d1", "P41")
    action, effects = iv.on_key("1")
    assert action == Hangup(("P33",)) and effects[0].data == {"rank": 1, "course_id": "U1"}
    assert iv.answers["interest"] == "U1"


def test_the_story_words_are_kept_for_the_recommender():
    iv = Interview()
    run(iv, ["1", "1", "1", "1", "1", "3", "1", "4", "2", "1", "P", "1"])
    iv.on_recording(
        "/r.wav", 5, details={"transcript": "दस साल से", "transcript_en": "for ten years"}
    )
    assert iv.answers["story"] == "दस साल से" and iv.answers["story_en"] == "for ten years"
