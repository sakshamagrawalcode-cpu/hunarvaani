"""Server tests: a whole kiosk session over the WebSocket, the officer API, an Exotel call, and the
officer console (login, a live phone-demo call with its step-by-step traces, edit, erase)."""

import base64
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from hv.config import settings

TMP = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)  # Windows keeps open files locked
settings.db_path = Path(TMP.name) / "server.db"
settings.audio_dir = Path(TMP.name) / "audio"
settings.cards_dir = Path(TMP.name) / "cards"
settings.officer_user, settings.officer_password = "officer", "pw"
settings.exotel_token = "tok"
settings.models = "fake"

from starlette.testclient import TestClient  # noqa: E402

from hv.server import app  # noqa: E402

STORY = "मैं पाँच साल से घर पर सिलाई करती हूँ। 5 साल। सिलाई ही सीखनी है, पर घर छोड़कर नहीं जा सकती, बच्चे हैं।"
AUTH = ("Basic " + base64.b64encode(b"officer:pw").decode())


def kiosk_session(client: TestClient, answers: dict, device_pin: str = "411001") -> list[dict]:
    """Play a kiosk session: the page says hello with its PIN code, then every ask is answered by
    question key (spoken answers are sent as typed text, as the helper's "type" box does)."""
    seen = []
    with client.websocket_connect("/ws/kiosk") as ws:
        ws.send_text(json.dumps({"type": "hello", "device_pin": device_pin}))
        while True:
            try:
                msg = ws.receive_json()
            except Exception:
                break
            seen.append(msg)
            if msg["type"] == "end":
                break
            if msg["type"] == "ask":
                value = next((answers[k] for k in reversed(msg["keys"]) if k in answers), "")
                if isinstance(value, list):
                    value = value.pop(0) if len(value) > 1 else value[0]
                ws.send_text(json.dumps({"type": "answer", "value": value}))
    return seen


def tearDownModule():
    from hv.server import STORE
    STORE.db.close()  # so the temp folder can be deleted on Windows


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_and_kiosk_page(self):
        self.assertTrue(self.client.get("/health").json()["ok"])
        self.assertIn("HunarVaani", self.client.get("/kiosk").text)

    def test_kiosk_session_then_officer_view(self):
        answers = {"lang_hi": "1", "consent": "हाँ", "consent_ai": "हाँ", "returning": "नहीं",
                   "ask_name": "मेरा नाम Asha Kamble है", "ask_story": STORY, "say_age": "उनतीस साल",
                   "say_gender": "महिला", "say_education": "आठवीं तक", "say_travel": "पंद्रह किलोमीटर",
                   "review_ok": "हाँ", "tf_press_2": "1", "choose_prompt": "1", "confirm_choice": "हाँ",
                   "set_pin": "2468", "set_pin_again": "2468"}
        seen = kiosk_session(self.client, answers)
        kinds = [m.get("kind") for m in seen if m["type"] == "show"]
        self.assertIn("options", kinds)
        self.assertIn("card", kinds)
        card = [m for m in seen if m.get("kind") == "card"][0]["data"]
        self.assertEqual(card["name"], "Asha Kamble")
        self.assertIn("<svg", card["svg"])
        self.assertTrue((settings.cards_dir / f"{card['raw_id']}.svg").exists())

        self.assertEqual(self.client.get("/api/people").status_code, 401)
        rows = self.client.get("/api/people?district=MH-PUN&name=Asha", headers={"Authorization": AUTH}).json()
        self.assertEqual(rows[0]["hv_id"], card["raw_id"])
        person = self.client.get(f"/api/person/{card['hv_id']}", headers={"Authorization": AUTH}).json()
        self.assertTrue(person["options"])
        self.assertTrue(any(e["field"] == "emphasis.access" for e in person["profile"]["evidence"]))
        r = self.client.post(f"/api/person/{card['raw_id']}/status", headers={"Authorization": AUTH},
                             json={"status": "approved", "note": "documents seen"})
        self.assertTrue(r.json()["ok"])
        person = self.client.get(f"/api/person/{card['raw_id']}", headers={"Authorization": AUTH}).json()
        self.assertEqual(person["status"], "approved")
        page = self.client.get(f"/api/person/{card['raw_id']}/card", headers={"Authorization": AUTH})
        self.assertIn(card["hv_id"], page.text)
        self.assertIn("status:approved", [a["action"] for a in person["audit"]])

    def test_exotel_wrong_token_is_refused(self):
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/exotel/ws/wrong") as ws:
                ws.receive_json()

    def test_exotel_call_with_keys(self):
        with self.client.websocket_connect("/exotel/ws/tok") as ws:
            ws.send_text(json.dumps({"event": "connected"}))
            ws.send_text(json.dumps({"event": "start", "stream_sid": "s1",
                                     "start": {"from": "9800000000", "media_format": {"sample_rate": 8000}}}))
            for digit in ["1", "2"]:  # Hindi, then "no" to consent: the call ends politely
                while ws.receive_json().get("event") != "clear":
                    pass
                ws.send_text(json.dumps({"event": "dtmf", "dtmf": {"digit": digit}}))
            try:
                while True:
                    ws.receive_json()
            except Exception:
                pass
        db = sqlite3.connect(settings.db_path)
        rows = db.execute("SELECT end_reason FROM sessions WHERE channel='phone'").fetchall()
        db.close()
        self.assertIn(("completed",), rows)


def console_call(client: TestClient, answers: dict, line_pin: str = "411001", headers=None) -> list[dict]:
    """Play the console's live call: like the kiosk, plus `trace` messages for every decision."""
    seen = []
    with client.websocket_connect("/ws/console", headers=headers or {"Authorization": AUTH}) as ws:
        ws.send_text(json.dumps({"type": "hello", "device_pin": line_pin}))
        while True:
            try:
                msg = ws.receive_json()
            except Exception:
                break
            seen.append(msg)
            if msg["type"] == "end":
                break
            if msg["type"] == "ask":
                value = next((answers[k] for k in reversed(msg["keys"]) if k in answers), "")
                if isinstance(value, list):
                    value = value.pop(0) if len(value) > 1 else value[0]
                ws.send_text(json.dumps({"type": "answer", "value": value}))
    return seen


SUNITA = {"lang_hi": "1", "consent": "1", "consent_ai": "2", "returning": "2", "ask_name": "मेरा नाम Sunita Pawar है",
          "ask_story": "मैं खेत में मज़दूरी करती हूँ और पाँच साल से घर पर सिलाई भी करती हूँ। 5 साल। मैं सिलाई ही सीखनी "
                       "चाहती हूँ, पर घर छोड़कर नहीं जा सकती, बच्चे हैं। घुटने में दर्द रहता है।",
          "say_age": "अड़तालीस साल", "say_gender": "1", "say_education": "पाँचवीं तक", "say_travel": "दस किलोमीटर",
          "review_ok": "1", "tf_press_2": "1", "choose_prompt": "1", "confirm_choice": "1",
          "set_pin": "1357", "set_pin_again": "1357"}


class ConsoleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def login(self) -> TestClient:
        client = TestClient(app)
        self.assertEqual(client.post("/api/login", json={"user": "officer", "password": "pw"}).status_code, 200)
        return client

    def test_console_page_and_login(self):
        client = TestClient(app)
        self.assertIn("console.js", client.get("/officer").text)  # the page itself holds no data
        self.assertEqual(client.get("/api/me").status_code, 401)
        self.assertNotIn("www-authenticate", client.get("/api/me").headers)  # no browser pop-up
        self.assertEqual(client.post("/api/login", json={"user": "officer", "password": "nope"}).status_code, 401)
        r = client.post("/api/login", json={"user": "officer", "password": "pw"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("httponly", r.headers["set-cookie"].lower())
        self.assertEqual(client.get("/api/me").json()["user"], "officer")
        self.assertTrue(client.get("/api/catalog").json()["districts"])
        # a cookie login is not honoured from another site's page
        self.assertEqual(client.get("/api/me", headers={"Origin": "https://evil.example"}).status_code, 401)
        client.post("/api/logout")
        self.assertEqual(client.get("/api/me").status_code, 401)

    def test_live_call_needs_a_login(self):
        with self.assertRaises(Exception):
            with TestClient(app).websocket_connect("/ws/console") as ws:
                ws.receive_json()

    def test_live_phone_demo_call_traces_every_decision(self):
        seen = console_call(self.client, dict(SUNITA))
        traces = [m for m in seen if m["type"] == "trace"]
        steps = [t["step"] for t in traces]
        for step in ("key", "heard", "llm", "rules", "plan", "review", "ranking", "choice", "saved"):
            self.assertIn(step, steps)
        # the LLM's labels, in plain words, with the person's own quote behind the emphasis
        llm = next(t for t in traces if t["step"] == "llm" and t["data"]["question"] == "ask_story")
        self.assertTrue(any("Tailor" in line for line in llm["lines"]))
        self.assertTrue(any("staying close to home" in line and "“" in line for line in llm["lines"]))
        # every question says why it was asked, and what else was open
        plan = next(t for t in traces if t["step"] == "plan")
        self.assertTrue(plan["lines"][0].startswith("Picked"))
        self.assertTrue(plan["data"]["candidates"])
        # the ranking: score = gates x fit for each option, and heavy work left out because of her knee
        ranking = next(t for t in traces if t["step"] == "ranking")["data"]
        self.assertTrue(ranking["options"])
        self.assertIn("× gates", ranking["options"][0]["sentence"])
        self.assertTrue(any("physical load" in b for x in ranking["left_out"] for b in x["because"]))
        # it is saved as a phone demo, with the explanation the person page shows
        hv_id = next(t for t in traces if t["step"] == "saved")["data"]["hv_id"]
        person = self.client.get(f"/api/person/{hv_id}", headers={"Authorization": AUTH}).json()
        self.assertEqual((person["name"], person["channel"]), ("Sunita Pawar", "phone-demo"))
        self.assertTrue(person["explain"]["lines"])
        self.assertEqual(len(person["explain"]["options"]), len(person["options"]))

    def test_edit_and_erase(self):
        seen = console_call(self.client, dict(SUNITA))
        hv_id = next(m for m in seen if m["type"] == "trace" and m["step"] == "saved")["data"]["hv_id"]
        client = self.login()
        url = f"/api/person/{hv_id}"
        self.assertEqual(client.patch(url, json={"age": 200}).status_code, 400)
        self.assertEqual(client.patch(url, json={"occupation_codes": [1]}).status_code, 400)
        r = client.patch(url, json={"age": 30, "health": "none", "radius_km": 30, "rerank": True,
                                    "note": "checked her documents"}).json()
        self.assertEqual(sorted(r["changed"]), ["age", "health", "radius_km"])
        self.assertTrue(r["reranked"])
        self.assertEqual(r["person"]["profile"]["age"], 30)
        edit = [a for a in r["person"]["audit"] if a["action"] == "edited"][-1]
        self.assertIn("48", edit["note"])
        self.assertIn("checked her documents", edit["note"])
        # erase: the ID must be typed to confirm; afterwards only the audit line is left
        self.assertEqual(client.request("DELETE", url, json={"confirm": "nope"}).status_code, 400)
        self.assertTrue((settings.cards_dir / f"{hv_id}.svg").exists())
        self.assertTrue(client.request("DELETE", url, json={"confirm": hv_id}).json()["ok"])
        self.assertEqual(client.get(url).status_code, 404)
        self.assertFalse((settings.cards_dir / f"{hv_id}.svg").exists())
        db = sqlite3.connect(settings.db_path)
        left = db.execute("SELECT actor, action FROM audit WHERE hv_id=? AND action='erased'", (hv_id,)).fetchall()
        options = db.execute("SELECT COUNT(*) FROM options WHERE hv_id=?", (hv_id,)).fetchone()[0]
        db.close()
        self.assertEqual((left, options), ([("officer", "erased")], 0))


if __name__ == "__main__":
    unittest.main()
