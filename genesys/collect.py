"""Genesys Ireland -> public AEDATS snapshot. Never exports credentials or user data by default."""
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = "https://api.mypurecloud.ie/api/v2"
AUTH = "https://login.mypurecloud.ie/oauth/token"
QUEUES = ("Ger-On-Site", "GER_Installer")
AGENTS = ("DA Service", "yechuan.chen")

class Genesys:
    def __init__(self):
        self.client_id = os.environ["GENESYS_CLIENT_ID"]
        self.secret = os.environ["GENESYS_CLIENT_SECRET"]
        self.session = requests.Session()
        self.token = None
        self.expiry = 0

    def authenticate(self):
        response = self.session.post(
            AUTH, auth=(self.client_id, self.secret),
            data={"grant_type": "client_credentials"}, timeout=30
        )
        response.raise_for_status()
        obj = response.json()
        self.token = obj["access_token"]
        self.expiry = time.monotonic() + max(1, int(obj.get("expires_in", 3600)) - 90)

    def request(self, method, path, **kwargs):
        for attempt in range(6):
            if not self.token or time.monotonic() >= self.expiry:
                self.authenticate()
            try:
                result = self.session.request(
                    method, BASE + path, headers={
                        "Authorization": "Bearer " + self.token,
                        "Accept": "application/json",
                    }, timeout=60, **kwargs
                )
            except (requests.ConnectionError, requests.Timeout):
                if attempt == 5:
                    raise
                time.sleep(min(30, 2 ** attempt + random.random()))
                continue
            if result.status_code == 401 and attempt == 0:
                self.authenticate()
                continue
            if result.status_code in (429, 500, 502, 503, 504) and attempt < 5:
                try:
                    wait = float(result.headers.get("Retry-After", ""))
                except ValueError:
                    wait = 2 ** attempt + random.random()
                time.sleep(min(60, max(0.1, wait)))
                continue
            result.raise_for_status()
            return result.json()
        raise RuntimeError("Genesys retries exhausted")

    def pages(self, path):
        output = []
        page = 1
        while True:
            data = self.request("GET", path, params={
                "pageSize": 100, "pageNumber": page
            })
            output.extend(data.get("entities", []))
            if page >= int(data.get("pageCount", 1)):
                return output
            page += 1

    def query(self, path, queue_ids, metrics, start=None, end=None, user_ids=None):
        queue_preds = [
            {"type": "dimension", "dimension": "queueId", "value": q}
            for q in queue_ids
        ]
        clauses = [
            {"type": "or", "predicates": queue_preds},
            {"type": "or", "predicates": [
                {"type": "dimension", "dimension": "mediaType", "value": "voice"}
            ]},
        ]
        if user_ids is not None:
            clauses.append({"type": "or", "predicates": [
                {"type": "dimension", "dimension": "userId", "value": u}
                for u in user_ids
            ]})
        body = {
            "filter": {"type": "and", "clauses": clauses},
            "metrics": metrics,
        }
        if start:
            body["interval"] = start + "/" + end
            body["groupBy"] = ["queueId", "userId"] if user_ids is not None else ["queueId"]
        else:
            body["detailMetrics"] = ["oWaiting"]
        return self.request("POST", path, json=body)

def lookup(items, names, keys):
    found = {}
    for name in names:
        choices = {
            x["id"] for x in items
            if any(
                str(x.get(key, "")).strip().casefold() == name.casefold()
                for key in keys
            )
        }
        if len(choices) != 1:
            raise RuntimeError(
                f"Genesys identity {name!r} expected 1 match, found {len(choices)}"
            )
        found[name] = next(iter(choices))
    return found

def parse_time(value):
    if not isinstance(value, str):
        return None
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except ValueError:
        return None

def observation_values(payload, queue_ids, now):
    data = {
        q: {"waiting": 0, "interacting": 0, "alerting": 0,
            "longest_wait_seconds": None, "longest_wait_source": "unavailable",
            "observation_details_count": 0}
        for q in queue_ids
    }
    fields = {"oWaiting": "waiting", "oInteracting": "interacting", "oAlerting": "alerting"}
    for group in payload.get("results", []):
        dimensions = group.get("group") or {}
        q = dimensions.get("queueId")
        if q not in data or dimensions.get("mediaType", "voice") != "voice":
            continue
        for metric in group.get("data", []):
            m = metric.get("metric")
            if m in fields:
                data[q][fields[m]] += int((metric.get("stats") or {}).get("count") or 0)
            if m == "oWaiting":
                for detail in metric.get("observations") or []:
                    begin = parse_time(detail.get("startTime"))
                    if begin:
                        seconds = max(0, (now - begin).total_seconds())
                        old = data[q]["longest_wait_seconds"]
                        data[q]["longest_wait_seconds"] = max(old or 0, seconds)
                        data[q]["longest_wait_source"] = "observation_start_time"
                        data[q]["observation_details_count"] += 1
    for item in data.values():
        if item["longest_wait_seconds"] is not None:
            item["longest_wait_seconds"] = round(item["longest_wait_seconds"], 1)
    return data

def stats_by_group(payload, expected, keys, metrics):
    rows = {key: {m: {"count": 0, "sum": 0.0} for m in metrics} for key in expected}
    for group in payload.get("results", []):
        dimensions = group.get("group") or {}
        key = tuple(dimensions.get(k) for k in keys)
        if key not in rows or dimensions.get("mediaType", "voice") != "voice":
            continue
        for bucket in group.get("data", []):
            for metric in bucket.get("metrics", []):
                name = metric.get("metric")
                if name not in metrics:
                    continue
                stats = metric.get("stats") or {}
                rows[key][name]["count"] += int(stats.get("count") or 0)
                rows[key][name]["sum"] += float(stats.get("sum") or 0)
    return rows

def main():
    client = Genesys()
    queue_list = client.pages("/routing/queues")
    queue_ids = lookup(queue_list, QUEUES, ("name",))
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=30)
    iso = lambda x: x.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    ids = list(queue_ids.values())
    observations = client.query("/analytics/queues/observations/query",
                                ids, ["oWaiting", "oInteracting", "oAlerting"])
    aggregates = client.query("/analytics/conversations/aggregates/query",
                              ids, ["nOffered", "tAnswered", "tAbandon"],
                              iso(start), iso(now))
    live = observation_values(observations, ids, now)
    agg = stats_by_group(aggregates, [(q,) for q in ids],
                         ("queueId",), ("nOffered", "tAnswered", "tAbandon"))
    result = {
        "schema_version": 1, "generated_at_utc": iso(now),
        "period_start_utc": iso(start), "period_end_utc": iso(now),
        "region": "mypurecloud.ie", "queues": [], "workload": [],
        "workload_published": False,
    }
    for name, qid in queue_ids.items():
        m = agg[(qid,)]
        offered = m["nOffered"]["count"]
        answered = m["tAnswered"]["count"]
        abandoned = m["tAbandon"]["count"]
        result["queues"].append({
            "queue_name": name,
            "live": live[qid],
            "kpi": {
                "offered": offered, "answered": answered, "abandoned": abandoned,
                "answer_rate": round(answered / offered, 5) if offered else None,
                "abandon_rate": round(abandoned / offered, 5) if offered else None,
                "asa_seconds": round(m["tAnswered"]["sum"] / answered / 1000, 2) if answered else None,
            }
        })
    if os.getenv("PUBLISH_PERSONAL_WORKLOAD", "false").lower() == "true":
        users = client.pages("/users")
        agents = lookup(users, AGENTS, ("name", "username"))
        a = client.query(
            "/analytics/conversations/aggregates/query", ids,
            ["tAnswered", "tHandle", "tTalk", "tAcw"], iso(start), iso(now),
            list(agents.values()),
        )
        keys = [(q, uid) for q in ids for uid in agents.values()]
        by_user = stats_by_group(a, keys, ("queueId", "userId"),
                                 ("tAnswered", "tHandle", "tTalk", "tAcw"))
        for agent, uid in agents.items():
            for queue, qid in queue_ids.items():
                m = by_user[(qid, uid)]
                result["workload"].append({
                    "agent_name": agent, "queue_name": queue,
                    "answered": m["tAnswered"]["count"],
                    "handle_seconds": round(m["tHandle"]["sum"] / 1000, 2),
                    "talk_seconds": round(m["tTalk"]["sum"] / 1000, 2),
                    "acw_seconds": round(m["tAcw"]["sum"] / 1000, 2),
                })
        result["workload_published"] = True
    path = Path("data/genesys.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    print("Wrote snapshot for", ", ".join(QUEUES))

if __name__ == "__main__":
    main()
