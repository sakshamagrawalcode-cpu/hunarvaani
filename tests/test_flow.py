from core.dialogue.flow import Ask, Hangup, Interview, Record


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
    action, effects = run(iv, ["1", "1", "1", "1", "2", "4", "2", "1"])
    assert isinstance(action, Record) and action.prompts == ("P12",)
    answers = {e.data["step"]: e.data["value"] for e in effects if e.kind == "answer"}
    assert answers == {"q_education": "10th", "q_travel": "10km", "q_lean": "job"}
    consents = [(e.data["kind"], e.data["granted"]) for e in effects if e.kind == "consent"]
    assert consents == [("recording", True), ("share", True), ("research", False)]

    action, effects = iv.on_recording("/rec/a.wav", 12.34)
    assert kinds(effects) == ["story_recorded"] and effects[0].data["seconds"] == 12.3
    assert action.prompts == ("P14",)
    action, effects = iv.on_key("2")
    assert effects[0].data == {"step": "trades", "key": "2", "value": "7531"}
    assert action == Hangup() and iv.state == "ended"


def test_language_menu_is_skipped_without_a_second_language():
    iv = Interview()
    iv.start()
    iv.on_key("1")
    action, _ = iv.on_key("1")
    assert action.prompts == ("P06",)


def test_language_menu_with_a_second_language():
    iv = Interview(second_language="mr-IN")
    run(iv, ["1", "1"])
    assert iv.state == "language"
    action, effects = iv.on_key("2")
    assert effects[0].data == {"code": "mr-IN"} and iv.language == "mr-IN"
    assert action.prompts == ("P06",)


def test_no_to_recording_means_keypad_only_and_no_story():
    iv = Interview()
    action, effects = run(iv, ["1", "1", "2", "1", "1", "3", "3", "2"])
    assert "keypad_only" in kinds(effects) and iv.keypad_only
    assert isinstance(action, Ask) and action.prompts == ("P14",)


def test_timeout_repeats_once_with_p16_then_skips():
    iv = Interview()
    run(iv, ["1", "1", "1", "1", "1"])
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
    assert action.prompts == ("P16", "P09")


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
    iv = Interview(second_language="ta-IN")
    run(iv, ["1", "1", "2"])
    copy = Interview.from_dict(iv.to_dict())
    assert copy == iv
    assert copy.on_key("1")[0] == iv.on_key("1")[0]


def test_empty_story_records_nothing_and_offers_the_trade_list():
    iv = Interview()
    run(iv, ["1", "1", "1", "1", "1", "4", "2", "1"])
    action, effects = iv.on_recording(None, 0.0)
    assert kinds(effects) == ["story_empty"] and action.prompts == ("P14",)
