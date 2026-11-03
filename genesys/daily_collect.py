"""Daily AEDATS snapshot; reporting period is midnight Berlin until collection."""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from genesys.collect import Genesys, QUEUES, AGENTS, lookup, observation_values, stats_by_group

def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def main():
    client = Genesys()
    queue_ids = lookup(client.pages("/routing/queues"), QUEUES, ("name",))
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo("Europe/Berlin"))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    ids = list(queue_ids.values())
    obs = client.query("/analytics/queues/observations/query", ids,
                       ["oWaiting", "oInteracting", "oAlerting"])
    agg = client.query("/analytics/conversations/aggregates/query", ids,
                       ["nOffered", "tAnswered", "tAbandon"],
                       iso(start), iso(now))
    live = observation_values(obs, ids, now)
    groups = stats_by_group(agg, [(q,) for q in ids], ("queueId",),
                            ("nOffered", "tAnswered", "tAbandon"))
    result = {
        "schema_version": 1, "generated_at_utc": iso(now),
        "report_date": local.date().isoformat(), "report_timezone": "Europe/Berlin",
        "period_start_utc": iso(start), "period_end_utc": iso(now),
        "queues": [], "workload": [], "workload_published": False
    }
    for name, qid in queue_ids.items():
        m = groups[(qid,)]
        offered = m["nOffered"]["count"]
        answered = m["tAnswered"]["count"]
        abandoned = m["tAbandon"]["count"]
        result["queues"].append({
            "queue_name": name,
            "live": live[qid],
            "kpi": {
                "offered": offered,
                "answered": answered,
                "abandoned": abandoned,
                "answer_rate": round(answered / offered, 5) if offered else None,
                "abandon_rate": round(abandoned / offered, 5) if offered else None,
                "asa_seconds": round(m["tAnswered"]["sum"] / answered / 1000, 2) if answered else None
            }
        })
    # Public GitHub Pages: intentionally do not publish any per-person performance.
    target = Path("data/genesys.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Daily queue snapshot generated for", local.date())

if __name__ == "__main__":
    main()
