from xml.sax.saxutils import escape

REJECT = '<Response><Hangup reason="rejected"/></Response>'
HANGUP = "<Response><Hangup/></Response>"


def play_then_hangup(*audio_urls: str) -> str:
    plays = "".join(f"<Play>{escape(u)}</Play>" for u in audio_urls)
    return f"<Response>{plays}<Hangup/></Response>"
