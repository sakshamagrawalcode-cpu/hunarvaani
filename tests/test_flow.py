from core.dialogue.flow import Ask, Effect, Hangup, Interview, Record


def kinds(effects):
    return [e.kind for e in effects]


def run(iv, keys):
    """Press keys in order; return (last action, all effects)."""
    effects = []
    action = iv.start()
    for k in keys:
        action, eff = iv.on_timeout() if k == "T" else iv.on_key(k)
        effects += eff
    return action, effects


def test_happy_path_with_recording():
    iv = Interview()
    action, effects = run(iv, ["1", "1", "1", "1", "2", "3", "1", "4", "2", "2", "1"])
    assert isinstance(action, Record) and action.prompts == ("P12",)
    answers = {e.data["step"]: e.data["value"] for e in effects if e.kind == "answer"}
    assert answers == {
        "q_age": "26_35",
        "q_gender": "female",
        "q_education": "10th",
        "q_travel": "10km",
        "q_physical": "some",
        "q_lean": "job",
    }
    consents = [(e.data["kind"], e.data["granted"]) for e in effects if e.kind == "consent"]
    assert consents == [("recording", True), ("share", True), ("research", False)]

    action, effects = iv.on_recording("/rec/a.wav", 12.34, understood=False)
    assert kinds(effects) == ["story_recorded"] and effects[0].data["seconds"] == 12.3
    assert action.prompts == ("P14",)
    action, effects = iv.on_key("2")
    assert effects[0].data == {"step": "trades", "key": "2", "value": "7531"}
    assert action == Hangup(("P15",)) and iv.state == "ended"
    assert (iv.education, iv.occupation) == ("10th", "7531")


def test_language_menu_is_skipped_with_one_language():
    iv = Interview()
    action = iv.on_key("1")[0]
    assert action.prompts == ("P03",) and iv.language == "hi-IN"
    action, _ = iv.on_key("1")
    assert action.prompts == ("P06",)


def test_language_menu_comes_right_after_the_greeting():
    iv = Interview(languages=["hi-IN", "en-IN", "mr-IN"])
    action, _ = iv.on_key("1")
    assert iv.state == "language"
    assert action.prompts == ("P05@hi-IN", "P05@en-IN", "P05@mr-IN")
    assert action.valid == "123" + "90"
    action, effects = iv.on_key("3")
    assert effects[0].data == {"code": "mr-IN"} and iv.language == "mr-IN"
    assert action.prompts == ("P03",) and iv.state == "safe_to_talk"


def test_language_keys_stay_fixed_when_one_is_left_out():
    iv = Interview(languages=["hi-IN", "mr-IN"])
    action, _ = iv.on_key("1")
    assert action.prompts == ("P05@hi-IN", "P05@mr-IN") and action.valid == "13" + "90"
    iv.on_key("2")
    assert iv.state == "language"
    iv.on_key("3")
    assert iv.language == "mr-IN"


def test_no_language_choice_keeps_hindi():
    iv = Interview(languages=["hi-IN", "en-IN"])
    iv.on_key("1")
    iv.on_timeout()
    action, effects = iv.on_timeout()
    assert effects == [Effect("skipped", {"step": "language"})]
    assert iv.language == "hi-IN" and action.prompts == ("P03",)


def test_no_to_recording_means_keypad_only_and_no_story():
    iv = Interview()
    action, effects = run(iv, ["1", "1", "2", "1", "1", "3", "1", "3", "3", "1", "2"])
    assert "keypad_only" in kinds(effects) and iv.keypad_only
    assert isinstance(action, Ask) and action.prompts == ("P14",)


def test_timeout_repeats_once_with_p16_then_skips():
    iv = Interview()
    run(iv, ["1", "1", "1", "1", "1", "3", "1"])
    assert iv.state == "q_education"
    action, effects = iv.on_timeout()
    assert action.prompts == ("P16", "P09") and effects == []
    action, effects = iv.on_timeout()
    assert effects[0].data == {"step": "q_education"} and effects[0].kind == "skipped"
    assert action.prompts == ("P10",)


def test_wrong_key_counts_like_a_timeout():
    iv = Interview()
    run(iv, ["1", "1", "1", "1", "1"])
    action, _ = iv.on_key("8")
    assert action.prompts == ("P16", "P25")


def test_age_gender_and_physical_questions_come_around_education():
    iv = Interview()
    action, _ = run(iv, ["1", "1", "1", "1", "1"])
    assert action.prompts == ("P25",) and action.valid == "123456" + "90"
    action, _ = iv.on_key("6")
    assert action.prompts == ("P26",) and action.valid == "1234" + "90"
    action, _ = iv.on_key("4")
    assert action.prompts == ("P09",)
    iv.on_key("7")
    action, _ = iv.on_key("5")
    assert action.prompts == ("P27",) and action.valid == "12" + "90"
    action, effects = iv.on_key("1")
    assert action.prompts == ("P11",)
    assert effects[0].data == {"step": "q_physical", "key": "1", "value": "none"}


def test_skipped_consent_counts_as_no():
    iv = Interview()
    run(iv, ["1", "1"])
    iv.on_timeout()
    _, effects = iv.on_timeout()
    assert kinds(effects) == ["skipped", "consent", "keypad_only"]
    assert effects[1].data["granted"] is False


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


def test_silent_opening_warns_then_hangs_up():
    iv = Interview()
    iv.start()
    action, _ = iv.on_timeout()
    assert action.prompts == ("P02",)
    action, effects = iv.on_timeout()
    assert action == Hangup() and kinds(effects) == ["no_response"]


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


def test_no_speech_asks_once_more_then_offers_the_trade_list():
    iv = Interview()
    run(iv, ["1", "1", "1", "1", "1", "3", "1", "4", "2", "1", "1"])
    action, effects = iv.on_recording(None, 0.0)
    assert kinds(effects) == ["story_empty"]
    assert isinstance(action, Record) and action.prompts == ("P22", "P23")
    action, effects = iv.on_recording(None, 0.0)
    assert kinds(effects) == ["story_empty"] and action.prompts == ("P22", "P14")


def _story(iv):
    run(iv, ["1", "1", "1", "1", "1", "3", "1", "4", "2", "1", "1"])


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
    assert action == Hangup(("P15",)) and iv.occupation == "7411"
    assert effects[0].data == {"key": "2", "confirmed": "7411", "candidates": ["7531", "7411"]}
    assert effects[1].data == {"step": "occupation", "key": "2", "value": "7411"}


def test_neither_lets_the_caller_tell_it_again_once():
    iv = Interview()
    _story(iv)
    iv.on_recording("/r.wav", 5, ["7531", "7411"], readback=["DYN:bb"], heard=["DYN:aa"])
    action, effects = iv.on_key("3")
    assert isinstance(action, Record) and action.prompts == ("P23",)
    assert effects[0].data["confirmed"] is None
    iv.on_recording("/r2.wav", 5, ["7531", "7411"], readback=["DYN:dd"], heard=["DYN:cc"])
    action, _ = iv.on_key("3")
    assert action.prompts == ("P14",)


def test_read_back_timeouts_repeat_then_fall_back():
    iv = Interview()
    _story(iv)
    iv.on_recording("/r.wav", 5, ["7531", "7411"], readback=["DYN:bb"], heard=["DYN:aa"])
    action, _ = iv.on_timeout()
    assert action.prompts == ("P16", "DYN:aa", "DYN:bb")
    action, effects = iv.on_timeout()
    assert action.prompts == ("P14",) and kinds(effects) == ["skipped"]


def test_unclear_story_says_what_we_heard_and_asks_for_more_detail():
    iv = Interview()
    _story(iv)
    action, effects = iv.on_recording("/r.wav", 5, [], None, {"top1": "5142"}, heard=["DYN:aa"])
    assert kinds(effects) == ["story_recorded"]
    assert isinstance(action, Record) and action.prompts == ("DYN:aa", "P24", "P23")
    action, _ = iv.on_recording("/r2.wav", 5, [], None, heard=["DYN:cc"])
    assert action.prompts == ("DYN:cc", "P24", "P14")


def test_second_story_can_be_confirmed():
    iv = Interview()
    _story(iv)
    iv.on_recording("/r.wav", 5, [], None, heard=["DYN:aa"])
    action, _ = iv.on_recording("/r2.wav", 5, ["7231", "7233"], readback=["DYN:dd"])
    assert action.step == "readback"
    action, _ = iv.on_key("1")
    assert action == Hangup(("P15",)) and iv.occupation == "7231"


def test_slow_or_failed_processing_goes_straight_to_the_trade_list():
    iv = Interview()
    _story(iv)
    action, _ = iv.on_recording("/r.wav", 5, understood=False)
    assert action.prompts == ("P14",)


def test_skipped_trade_list_still_ends_with_the_summary():
    iv = Interview()
    run(iv, ["1", "1", "2", "1", "1", "3", "1", "3", "3", "1", "2"])
    iv.on_timeout()
    action, effects = iv.on_timeout()
    assert action == Hangup(("P15",)) and iv.occupation == "" and kinds(effects) == ["skipped"]
