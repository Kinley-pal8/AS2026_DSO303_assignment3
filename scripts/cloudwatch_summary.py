"""Pull the CloudWatch evidence for one load-test run (Assignment 3).

Reads the run's time window from evidence/load-test-<label>.json, then prints and saves
evidence/cloudwatch-<label>.md with:
  - metrics: API Gateway, Lambda (api function), RDS and DynamoDB, one-minute periods
  - Logs Insights: Lambda REPORT lines (cold starts, @initDuration) and the db_connect lines
    written by backend/db.py (time to connect and to run the schema statements)

Usage (CloudShell, from the repo root, after the run):
  python3 scripts/cloudwatch_summary.py run1-t4g-micro

Metrics can take 2-3 minutes to appear; if a value is missing, wait and run it again.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time

import boto3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "evidence")
PAD = dt.timedelta(minutes=1)


def tf_outputs():
    out = subprocess.run(["terraform", f"-chdir={os.path.join(ROOT, 'infra')}", "output", "-json"],
                         check=True, capture_output=True, text=True).stdout
    return {k: v["value"] for k, v in json.loads(out).items()}


def metric_rows(cw, start, end, specs):
    """specs: (label, namespace, metric, dimensions, stat, how) with how in max|min|sum."""
    queries = [{"Id": f"m{i}", "Label": s[0], "ReturnData": True,
                "MetricStat": {"Metric": {"Namespace": s[1], "MetricName": s[2],
                                          "Dimensions": [{"Name": k, "Value": v} for k, v in s[3].items()]},
                               "Period": 60, "Stat": s[4]}} for i, s in enumerate(specs)]
    res = {r["Id"]: r["Values"] for r in cw.get_metric_data(MetricDataQueries=queries, StartTime=start,
                                                             EndTime=end)["MetricDataResults"]}
    rows = []
    for i, s in enumerate(specs):
        vals = res.get(f"m{i}", [])
        if not vals:
            value = "no data"
        else:
            value = {"max": max, "min": min, "sum": sum}[s[5]](vals)
            value = f"{value:,.1f}"
        rows.append((s[0], f"{s[4]}, {s[5]} of 1-min values", value))
    return rows


def insights(logs, group, start, end, query):
    qid = logs.start_query(logGroupName=group, startTime=int(start.timestamp()), endTime=int(end.timestamp()),
                           queryString=query)["queryId"]
    while True:
        r = logs.get_query_results(queryId=qid)
        if r["status"] in ("Complete", "Failed", "Cancelled", "Timeout"):
            break
        time.sleep(1)
    return [{f["field"]: f["value"] for f in row} for row in r.get("results", [])]


def main(label):
    run = json.load(open(os.path.join(EVIDENCE, f"load-test-{label}.json")))
    start = dt.datetime.fromisoformat(run["started_utc"]) - PAD
    end = dt.datetime.fromisoformat(run["ended_utc"]) + PAD
    o = tf_outputs()
    api_id = o["api_endpoint_direct"].split("//")[1].split(".")[0]
    db, table = o["db_instance_id"], o["attempts_table"]
    fn = db.rsplit("-db", 1)[0] + "-api"

    api = {"ApiId": api_id, "Stage": "$default"}
    lam = {"FunctionName": fn}
    rds = {"DBInstanceIdentifier": db}
    ddb = {"TableName": table}
    specs = [
        ("API Gateway requests", "AWS/ApiGateway", "Count", api, "Sum", "sum"),
        ("API Gateway latency p95 (ms)", "AWS/ApiGateway", "Latency", api, "p95", "max"),
        ("API Gateway latency p99 (ms)", "AWS/ApiGateway", "Latency", api, "p99", "max"),
        ("API Gateway 5xx", "AWS/ApiGateway", "5xx", api, "Sum", "sum"),
        ("API Gateway 4xx", "AWS/ApiGateway", "4xx", api, "Sum", "sum"),
        ("Lambda concurrent executions", "AWS/Lambda", "ConcurrentExecutions", lam, "Maximum", "max"),
        ("Lambda duration p95 (ms)", "AWS/Lambda", "Duration", lam, "p95", "max"),
        ("Lambda duration p99 (ms)", "AWS/Lambda", "Duration", lam, "p99", "max"),
        ("Lambda duration max (ms)", "AWS/Lambda", "Duration", lam, "Maximum", "max"),
        ("Lambda throttles", "AWS/Lambda", "Throttles", lam, "Sum", "sum"),
        ("Lambda errors", "AWS/Lambda", "Errors", lam, "Sum", "sum"),
        ("RDS CPU (%)", "AWS/RDS", "CPUUtilization", rds, "Maximum", "max"),
        ("RDS CPU credit balance", "AWS/RDS", "CPUCreditBalance", rds, "Minimum", "min"),
        ("RDS connections", "AWS/RDS", "DatabaseConnections", rds, "Maximum", "max"),
        ("RDS read latency (s)", "AWS/RDS", "ReadLatency", rds, "Maximum", "max"),
        ("RDS write latency (s)", "AWS/RDS", "WriteLatency", rds, "Maximum", "max"),
        ("RDS freeable memory (bytes)", "AWS/RDS", "FreeableMemory", rds, "Minimum", "min"),
        ("DynamoDB write units consumed", "AWS/DynamoDB", "ConsumedWriteCapacityUnits", ddb, "Sum", "sum"),
        ("DynamoDB UpdateItem latency (ms)", "AWS/DynamoDB", "SuccessfulRequestLatency",
         {**ddb, "Operation": "UpdateItem"}, "Average", "max"),
        ("DynamoDB PutItem latency (ms)", "AWS/DynamoDB", "SuccessfulRequestLatency",
         {**ddb, "Operation": "PutItem"}, "Average", "max"),
        ("DynamoDB throttled requests", "AWS/DynamoDB", "ThrottledRequests", ddb, "Sum", "sum"),
    ]
    rows = metric_rows(boto3.client("cloudwatch"), start, end, specs)

    logs = boto3.client("logs")
    group = f"/aws/lambda/{fn}"
    report = insights(logs, group, start, end,
                      'filter type = "platform.report" '
                      "| stats count(*) as invocations, count(record.metrics.initDurationMs) as cold_starts, "
                      "avg(record.metrics.initDurationMs) as avg_init_ms, max(record.metrics.initDurationMs) as max_init_ms, "
                      "pct(record.metrics.durationMs, 95) as p95_duration_ms, max(record.metrics.durationMs) as max_duration_ms")
    first = insights(logs, group, start, end,
                     "filter message like /db_connect/ "
                     '| parse message "connect_ms=* schema_ms=*" as connect_ms, schema_ms '
                     "| stats count(*) as new_db_connections, avg(connect_ms) as avg_connect_ms, "
                     "max(connect_ms) as max_connect_ms, avg(schema_ms) as avg_schema_ms, max(schema_ms) as max_schema_ms")
    per_bin = insights(logs, group, start, end,
                       'filter type = "platform.report" '
                       "| stats count(record.metrics.initDurationMs) as cold_starts, "
                       "pct(record.metrics.durationMs, 99) as p99_duration_ms by bin(30s)")

    access = f"/aws/apigateway/{db.rsplit('-db', 1)[0]}"  # API Gateway access log (one line per request)
    try:
        slow = insights(logs, access, start, end,
                        "filter latencyMs >= 300 | stats count(*) as requests_over_300ms, "
                        "max(latencyMs) as max_ms by method")
        slowest = insights(logs, access, start, end,
                           "fields @timestamp, method, status, latencyMs | filter latencyMs >= 300 "
                           "| sort latencyMs desc | limit 20")
    except logs.exceptions.ResourceNotFoundException:
        slow = slowest = [{"note": f"{access} not found (enable_api_access_logs = false)"}]

    lines = [f"# CloudWatch summary: {label}", "",
             f"Window (UTC): {run['started_utc']} to {run['ended_utc']}, padded by 1 minute each side.",
             f"Resources: API {api_id}, Lambda {fn}, RDS {db}, DynamoDB {table}.", "",
             "## Metrics", "", "| Metric | Statistic | Value |", "| --- | --- | ---: |"]
    lines += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    lines += ["", "## Lambda REPORT lines (cold starts)", "", "```", json.dumps(report, indent=2), "```",
              "", "## New database connections (db_connect lines from backend/db.py)", "",
              "```", json.dumps(first, indent=2), "```",
              "", "## Cold starts and p99 duration per 30 seconds", "",
              "```", json.dumps(sorted(per_bin, key=lambda r: r.get("bin(30s)", "")), indent=2), "```",
              "", "## Requests that took 300 ms or more (API Gateway access log)", "",
              "```", json.dumps(slow, indent=2), "```", "", "Slowest 20:", "",
              "```", json.dumps(slowest, indent=2), "```"]
    text = "\n".join(lines) + "\n"
    path = os.path.join(EVIDENCE, f"cloudwatch-{label}.md")
    open(path, "w").write(text)
    print(text)
    print(f"saved {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
