"""Control checks are not a substitute for evaluating the investment thesis."""
import hashlib
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTUAL_LABELS = frozenset({"fact_source_reported", "fact_provider_standardized", "derived_calculation"})
EVIDENCE_LABELS = ACTUAL_LABELS | frozenset({
    "issuer_management_claim", "management_adjusted", "analyst_adjusted", "analyst_interpretation",
    "assumption_user_provided", "assumption_inferred", "estimate_consensus", "stale_source",
    "contradicted_source", "missing_required_source", "unknown", "scenario_assumption"})


def code_digest():
    paths = ("research.py", "assurance.py", "models.py", "monitoring.py", "sources.py", "store.py", "platform.py", "markets.py", "knowledge.py", "information.py", "reports.py")
    h = hashlib.sha256()
    for name in paths:
        h.update(name.encode())
        h.update((ROOT/"pfa"/name).read_bytes())
    for path in sorted((ROOT/'knowledge').glob('*.json')):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


# Deliberately freeze at process start; disk edits require a service restart.
RUNNING_KERNEL = code_digest()


@lru_cache(maxsize=256)
def file_hash(path, mtime_ns, size):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integrity(document):
    raw = Path(document.get("local_path", ""))
    if not raw.is_absolute():
        raw = ROOT/raw
    try:
        raw = raw.resolve()
        if (ROOT/"data/raw").resolve() not in raw.parents:
            return "outside_source_directory"
        stat = raw.stat()
        actual = file_hash(str(raw), stat.st_mtime_ns, stat.st_size)
        return "matched" if actual == document.get("sha256") else "hash_mismatch"
    except OSError:
        return "missing"


def temporal_actual(fact, today=None):
    today = today or date.today()
    try:
        end = date.fromisoformat(fact["period_end"])
        public = fact["source"].get("published_at")
        return bool(public) and end <= date.fromisoformat(public[:10]) <= today
    except (ValueError, TypeError):
        return False


def comparable_period(current, previous):
    if any(current.get(k) != previous.get(k) for k in ("unit", "currency", "scope", "basis")):
        return False
    try:
        a, b = date.fromisoformat(current["period_start"]), date.fromisoformat(current["period_end"])
        c, d = date.fromisoformat(previous["period_start"]), date.fromisoformat(previous["period_end"])
        # Tolerates 52/53-week fiscal calendars, not 18-month versus six-month series.
        return (350 <= (b-d).days <= 380 and 350 <= (a-c).days <= 380
                and abs((b-a).days-(d-c).days) <= 7)
    except (KeyError, TypeError, ValueError):
        return False
