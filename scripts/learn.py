"""Propose a new ranking policy from logged choices and verified outcomes.

  python scripts/learn.py            # writes config/proposed/<time>.json if there is enough data
An officer reviews the report and activates it on the officer console (or via /api/policy/activate).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hv.config import settings  # noqa: E402
from hv.data import get_data  # noqa: E402
from hv.learn import propose  # noqa: E402
from hv.policy import CONFIG, POLICIES  # noqa: E402
from hv.profile import Profile  # noqa: E402
from hv.store import Store  # noqa: E402


def main() -> None:
    store, data, pol = Store(settings.db_path), get_data(), POLICIES.active()
    people = [Profile.from_dict(store.person(r["hv_id"])["profile"]) for r in store.find(limit=5000)]
    result = propose(data, pol, store.choice_sets(), store.outcome_rows(), people)
    print(json.dumps(result["report"], indent=1, ensure_ascii=False))
    if not result["ok"]:
        print("\nNo proposal written.")
        return
    folder = CONFIG / "proposed"
    folder.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + ".json"
    (folder / name).write_text(json.dumps({"report": result["report"], "policy": result["policy"]}, indent=1,
                                          ensure_ascii=False), encoding="utf-8")
    print(f"\nProposal written: config/proposed/{name}. An officer must activate it.")


if __name__ == "__main__":
    main()
