"""What we know about one person, filled turn by turn from keypad answers and the LLM's labels."""

from dataclasses import asdict, dataclass, field

from .policy import FACTORS  # noqa: F401  (re-exported for older imports)

# the LLM's strength labels; hv/emphasis.py turns evidence into a multiplier using the policy
STRENGTH = ("insists", "prefers", "neutral", "doesnt_care")
MOODS = ("hopeful", "worried", "upset", "neutral")


@dataclass
class Profile:
    language: str = "hi"
    name: str = ""
    age: int | None = None
    gender: str | None = None  # female | male | other
    pin: str = ""
    district: str | None = None
    education: str | None = None
    radius_km: int | None = None  # how far they can travel each day
    hostel_ok: bool | None = None
    cannot_leave_home: bool = False
    health: str = "none"  # none | some | severe
    lean: str | None = None  # job | own_work | either
    occupation_codes: list[int] = field(default_factory=list)
    years: int | None = None
    skills: list[str] = field(default_factory=list)
    aspiration_codes: list[int] = field(default_factory=list)
    aspiration_sector: str | None = None
    family_code: int | None = None
    continue_family: bool | None = None
    emphasis: dict[str, str] = field(default_factory=dict)  # factor -> strength label
    evidence: list[dict] = field(default_factory=list)  # {"field", "quote"}: every label keeps the words
    moods: list[str] = field(default_factory=list)
    # from the guided follow-up questions
    max_weeks: int | None = None  # longest training they can do (None = not asked / any length)
    rejected_sectors: list[str] = field(default_factory=list)  # "no" to "this work could suit you: X"
    rejected_kinds: list[str] = field(default_factory=list)  # e.g. "certificate", "startup"
    confirmed_sectors: list[str] = field(default_factory=list)  # "yes" to the same question
    location_from: str = ""  # "device" (kiosk or phone line setting) or "asked"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)
