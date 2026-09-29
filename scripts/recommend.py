"""Show the training and livelihood options for a caller profile, from the sample dataset.

No database, phone or Sarvam needed. On the laptop:
  python scripts\\recommend.py --occupation 7531 --age 26_35 --gender female ^
      --education upto_8th --travel 10km --lean own_work --pin 411001

Values are the interview's answer values (see backend/core/dialogue/flow.py).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from core import geo  # noqa: E402
from core.dialogue.flow import AGE, EDUCATION, GENDER, LEAN, PHYSICAL, TRAVEL  # noqa: E402
from core.recommend import Profile, as_dict, recommend  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--occupation", required=True, help="NCO code, e.g. 7531 (tailor)")
    ap.add_argument("--age", choices=sorted(AGE.values()))
    ap.add_argument("--gender", choices=sorted(GENDER.values()))
    ap.add_argument("--education", choices=list(EDUCATION.values()))
    ap.add_argument("--travel", choices=list(TRAVEL.values()))
    ap.add_argument("--physical", choices=sorted(PHYSICAL.values()), default="none")
    ap.add_argument("--lean", choices=list(LEAN.values()))
    ap.add_argument("--pin", help="6-digit PIN code; gives the district")
    args = ap.parse_args()

    district = None
    if args.pin:
        row = geo.district_for_pin(args.pin)
        district = row["district_code"] if row else None
        print(f"PIN {args.pin}: {row['district_en'] + ', ' + row['state'] if row else 'not found'}")
    profile = Profile(
        args.occupation,
        args.age,
        args.gender,
        args.education,
        args.travel,
        args.physical,
        args.lean,
        district,
    )
    options = recommend(profile)
    if not options:
        print("No option fits this profile (age, education or occupation).")
    for o in options:
        d = as_dict(o)
        where = f"{d['centre']}, about {d['distance_km']} km" if d["centre"] else "centre unknown"
        print(f"\n{d['rank']}. {d['title']}  [{d['kind']}, NSQF {d['nsqf_level']}, {d['hours']} h]")
        print(f"   {where} | scheme: {d['scheme']} | score {d['score']}")
        for reason in d["reasons"]:
            print(f"   - {reason}")
        print(f"   skill gap: {', '.join(d['skill_gap']) or 'none (certificate)'}")
        if d["loan"]:
            print(f"   loan help: {d['loan']}")
    print("\nAll courses, centres, distances and numbers are SAMPLE data for the demonstration.")


if __name__ == "__main__":
    main()
