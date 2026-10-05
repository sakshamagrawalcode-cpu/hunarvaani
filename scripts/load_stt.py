"""Load IndicConformer once (installer step). If the model's own code needs a package we did not
install, transformers names it ("pip install x y"); install it and try again, up to three times."""

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    for attempt in range(3):
        try:
            from hv.stt import STT

            s = STT(real=True)
            s._load()
            print("    speech-to-text loads: OK")
            return 0
        except ImportError as exc:
            msg = str(exc)
            m = re.search(r"pip install ([\w\-\. ]+)", msg)
            if not m or attempt == 2:
                print(f"    speech-to-text failed to load: {msg}")
                return 1
            pkgs = m.group(1).split()
            print(f"    the model needs {pkgs}; installing ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", *pkgs])
            for name in list(sys.modules):  # forget the half-imported model code before retrying
                if name.startswith(("transformers_modules", "hv.stt")):
                    del sys.modules[name]
        except Exception as exc:
            print(f"    speech-to-text failed to load: {type(exc).__name__}: {exc}")
            return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
