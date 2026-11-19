"""Second-by-second view of a failure test (Assignment 3).

Builds a 10-second timeline of API responses from the API Gateway access log, adds the Lambda
Throttles metric and the history of the api-throttles alarm, and saves it as
evidence/failure-<name>-timeline.md. Use it to read the RTO: the time from the end of the fault
to the last error.

Usage (CloudShell, repo root):
  python3 scripts/failure_timeline.py <name> <start UTC> <end UTC> [event=time ...]
  e.g.
  python3 scripts/failure_timeline.py test2-throttle 2026-11-20T01:00:00 2026-11-20T01:08:00 \
      limit-on=2026-11-20T01:02:05 limit-off=2026-11-20T01:05:07
"""
import datetime as dt
import json
import os
import sys
import time

import boto3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = "uniexam-prod"


def utc(s):
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def insights(logs, group, start, end, query):
    qid = logs.start_query(logGroupName=group, startTime=int(start.timestamp()),
                           endTime=int(end.timestamp()), queryString=query)["queryId"]
    while True:
        r = logs.get_query_results(queryId=qid)
        if r["status"] in ("Complete", "Failed", "Cancelled", "Timeout"):
            return [{f["field"]: f["value"] for f in row} for row in r.get("results", [])]
        time.sleep(1)


def main(name, start, end, events):
    logs, cw = boto3.client("logs"), boto3.client("cloudwatch")
    group = f"/aws/apigateway/{PREFIX}"
    total = insights(logs, group, start, end, "stats count(*) as n by bin(10s)")
    bad = insights(logs, group, start, end,
                   "filter status >= 400 | stats count(*) as n by bin(10s), status")
    B = "bin(10s)"
    rows = {r[B]: {"requests": int(r["n"])} for r in total}
    for r in bad:
        rows.setdefault(r[B], {"requests": 0})[r["status"]] = int(r["n"])
    codes = sorted({k for v in rows.values() for k in v if k != "requests"})

    marks = sorted((t, label) for label, t in events.items())
    lines = [f"# Failure timeline: {name}", "",
             f"Window (UTC): {start.isoformat()} to {end.isoformat()}. Source: API Gateway access log "
             f"`{group}`, 10-second bins.", ""]
    if marks:
        lines += ["Events:", ""] + [f"- {t.isoformat()}: **{label}**" for t, label in marks] + [""]
    lines += ["| 10 s from (UTC) | Requests | " + " | ".join(f"HTTP {c}" for c in codes) + " | Error % | Event |",
              "| --- | ---: | " + " | ".join("---:" for _ in codes) + " | ---: | --- |"]
    first_err = last_err = None
    for t in sorted(rows):
        v = rows[t]
        errs = sum(v.get(c, 0) for c in codes)
        if errs:
            first_err = first_err or t
            last_err = t
        tt = utc(t.replace(" ", "T"))
        ev = ", ".join(label for m, label in marks if tt <= m < tt + dt.timedelta(seconds=10))
        pct = 100 * errs / v["requests"] if v["requests"] else 0
        lines.append(f"| {t[11:19]} | {v['requests']} | " + " | ".join(str(v.get(c, 0)) for c in codes)
                     + f" | {pct:.1f} | {ev} |")
    total_req = sum(v["requests"] for v in rows.values())
    total_err = sum(v.get(c, 0) for v in rows.values() for c in codes)
    lines += ["", f"Total: {total_req} requests, {total_err} errors "
                  f"({100 * total_err / max(1, total_req):.2f}%). First error bin: {first_err}. Last error bin: {last_err}.", ""]

    m = cw.get_metric_statistics(Namespace="AWS/Lambda", MetricName="Throttles",
                                 Dimensions=[{"Name": "FunctionName", "Value": f"{PREFIX}-api"}],
                                 StartTime=start, EndTime=end, Period=60, Statistics=["Sum"])
    lines += ["## Lambda Throttles (uniexam-prod-api, per minute)", "", "| Minute (UTC) | Throttles |", "| --- | ---: |"]
    lines += [f"| {p['Timestamp'].strftime('%H:%M')} | {p['Sum']:.0f} |"
              for p in sorted(m["Datapoints"], key=lambda p: p["Timestamp"])] or ["| (no data) | |"]
    h = cw.describe_alarm_history(AlarmName=f"{PREFIX}-api-throttles", HistoryItemType="StateUpdate",
                                  StartDate=start - dt.timedelta(minutes=5), EndDate=end + dt.timedelta(minutes=10))
    lines += ["", f"## Alarm `{PREFIX}-api-throttles` state changes", ""]
    lines += [f"- {a['Timestamp'].strftime('%H:%M:%S')} UTC: {a['HistorySummary']}"
              for a in sorted(h["AlarmHistoryItems"], key=lambda a: a["Timestamp"])] or ["- (no state change in this window)"]

    text = "\n".join(lines) + "\n"
    path = os.path.join(ROOT, "evidence", f"failure-{name}-timeline.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(text)
    print(text)
    print(f"saved {path}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    ev = dict(a.split("=", 1) for a in sys.argv[4:])
    main(sys.argv[1], utc(sys.argv[2]), utc(sys.argv[3]), {k: utc(v) for k, v in ev.items()})
