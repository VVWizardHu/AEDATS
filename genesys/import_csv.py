"""Convert a normalized, queue-only Genesys CSV export to the public AEDATS JSON."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE = Path("imports/genesys_daily.csv")
TARGET = Path("data/genesys.json")
NAMES = ("Ger-On-Site", "GER_Installer")

def nonnegative(value, field):
    try:
        number = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {field}: {value!r}")
    if number < 0:
        raise ValueError(f"Negative {field}")
    return number

def main():
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    found = {}
    for row in rows:
        name = (row.get("queue_name") or "").strip()
        if name not in NAMES:
            continue
        if name in found:
            raise ValueError(f"Duplicate queue: {name}")
        offered = nonnegative(row.get("offered"), "offered")
        answered = nonnegative(row.get("answered"), "answered")
        abandoned = nonnegative(row.get("abandoned"), "abandoned")
        if answered > offered or abandoned > offered:
            raise ValueError(f"Metrics inconsistent for {name}")
        # These are period totals, not live observation values.
        found[name] = {
            "queue_name": name,
            "live": {"waiting": None, "longest_wait_seconds": None,
                     "interacting": None, "alerting": None},
            "kpi": {
                "offered": offered, "answered": answered, "abandoned": abandoned,
                "answer_rate": round(answered / offered, 5) if offered else None,
                "abandon_rate": round(abandoned / offered, 5) if offered else None,
                "asa_seconds": None,
            },
        }
    if set(found) != set(NAMES):
        raise ValueError(f"Missing required queues: {set(NAMES) - set(found)}")
    date_str = (rows[0].get("report_date") or "").strip()
    try:
        report_day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("report_date must be YYYY-MM-DD")
    if any((row.get("report_date") or "").strip() != date_str
           for row in rows if row.get("queue_name") in NAMES):
        raise ValueError("Conflicting report_date values")
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo("Europe/Berlin"))
    if report_day > local.date():
        raise ValueError("Report date is in the future")
    output = {
        "schema_version": 1, "generated_at_utc": now.isoformat(),
        "report_date": date_str, "report_timezone": "Europe/Berlin",
        "source": "manual_csv",
        "queues": [found[name] for name in NAMES],
        "workload": [], "workload_published": False
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("Prepared daily report", date_str)

if __name__ == "__main__":
    main()
