"""Server tests: a whole kiosk session over the WebSocket, the officer API, and an Exotel call."""

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


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        from hv.server import STORE
        STORE.db.close()  # so the temp folder can be deleted on Windows

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


if __name__ == "__main__":
    unittest.main()
