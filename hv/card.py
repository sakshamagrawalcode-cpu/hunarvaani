"""The person's HunarVaani card: a printable file with their name, ID and a QR code.

Saved as cards/<id>.svg (the card) and cards/<id>.html (a print page). The QR holds only the ID
(HUNARVAANI:<id>), never the PIN, phone number or any other personal detail; an officer scans it and
looks the person up in the console. Erasing a person's data deletes their card files too.
"""

import html
import logging
from datetime import date
from pathlib import Path

from .config import settings
from .identity import pretty

log = logging.getLogger("hv.card")

W, H = 640, 400


def qr_payload(hv_id: str) -> str:
    return f"HUNARVAANI:{hv_id}"


def _qr_data_uri(hv_id: str) -> str | None:
    try:
        import segno
    except ImportError:  # the kiosk still draws its own QR in the browser
        log.warning("segno is not installed: the card file has no QR (pip install segno)")
        return None
    return segno.make(qr_payload(hv_id), error="m").svg_data_uri(scale=6, border=2)


def card_svg(hv_id: str, name: str, district: str, chosen: str = "", skills: list[str] | None = None,
             issued: str | None = None) -> str:
    e = html.escape
    issued = issued or date.today().isoformat()
    qr = _qr_data_uri(hv_id)
    qr_el = (f'<image x="430" y="110" width="180" height="180" href="{qr}"/>' if qr else
             '<rect x="430" y="110" width="180" height="180" fill="#eee"/>'
             '<text x="520" y="205" text-anchor="middle" font-size="14" fill="#666">QR</text>')
    lines = []
    y = 262
    if chosen:
        lines.append(f'<text x="32" y="{y}" font-size="15" fill="#5b5a7a">Chosen option</text>')
        lines.append(f'<text x="32" y="{y + 22}" font-size="17" font-weight="600">{e(chosen[:42])}</text>')
        y += 52
    if skills:
        lines.append(f'<text x="32" y="{y}" font-size="15" fill="#5b5a7a">Skills to learn</text>')
        rows, row = [], ""
        for sk in skills:  # wrap at about 46 characters, at most two lines
            nxt = f"{row}, {sk}" if row else sk
            if len(nxt) > 46 and row:
                rows.append(row)
                row = sk
            else:
                row = nxt
        rows.append(row)
        for i, r in enumerate(rows[:2]):
            lines.append(f'<text x="32" y="{y + 22 + 19 * i}" font-size="15">{e(r[:50])}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"
  font-family="Noto Sans, Noto Sans Devanagari, Nirmala UI, Mangal, Arial, sans-serif">
  <rect width="{W}" height="{H}" rx="22" fill="#ffffff" stroke="#2b2766" stroke-width="3"/>
  <rect width="{W}" height="76" rx="22" fill="#2b2766"/><rect y="50" width="{W}" height="26" fill="#2b2766"/>
  <text x="32" y="48" font-size="28" font-weight="700" fill="#ffffff">HunarVaani</text>
  <text x="{W - 32}" y="46" font-size="15" fill="#d9d7f5" text-anchor="end">हुनरवाणी · livelihood card</text>
  <text x="32" y="122" font-size="15" fill="#5b5a7a">Name</text>
  <text x="32" y="150" font-size="24" font-weight="700" fill="#1f1d4f">{e(name[:28] or "-")}</text>
  <text x="32" y="186" font-size="15" fill="#5b5a7a">HunarVaani ID</text>
  <text x="32" y="216" font-size="30" font-weight="700" fill="#2f8a57" letter-spacing="2">{e(pretty(hv_id))}</text>
  <text x="250" y="122" font-size="15" fill="#5b5a7a">District</text>
  <text x="250" y="150" font-size="18" fill="#1f1d4f">{e(district[:18] or "-")}</text>
  {qr_el}
  <text x="520" y="310" font-size="12" fill="#5b5a7a" text-anchor="middle">Issued {e(issued)}</text>
  {"".join(lines)}
  <text x="32" y="{H - 18}" font-size="12" fill="#b42318">Keep your PIN secret. HunarVaani never asks for money or an OTP.</text>
</svg>'''


def save_card(hv_id: str, svg: str) -> Path:
    folder = settings.cards_dir
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{hv_id}.svg"
    path.write_text(svg, encoding="utf-8")
    page = (f'<!doctype html><html><head><meta charset="utf-8"><title>HunarVaani card {pretty(hv_id)}</title>'
            '<style>body{margin:24px;font-family:sans-serif}@media print{button{display:none}}</style></head>'
            f'<body>{svg}<p><button onclick="print()">Print</button></p></body></html>')
    (folder / f"{hv_id}.html").write_text(page, encoding="utf-8")
    return path


def load_card(hv_id: str) -> str | None:
    path = settings.cards_dir / f"{hv_id}.svg"
    return path.read_text(encoding="utf-8") if path.exists() else None


def delete_card(hv_id: str) -> None:
    for ext in ("svg", "html"):
        (settings.cards_dir / f"{hv_id}.{ext}").unlink(missing_ok=True)
