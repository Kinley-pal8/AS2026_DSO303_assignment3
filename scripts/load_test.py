#!/usr/bin/env python3
"""Exam-peak load test for UniExam (Assignment 3).

Recreates the brief's peak at a scale a laptop can drive:
  phase 1  "start storm": N students start the same exam within S seconds
  phase 2  "autosave":    every student saves answers every I seconds for D seconds
With N=300 and I=3 s the autosave rate is ~100 writes/s - the same rate as 3,000 students
saving every 30 s. Results (count, rate, p50/p95/p99 latency, errors) are printed and saved
as JSON in evidence/. Read the matching CloudWatch graphs for the same time window.

Prerequisites (Learner Lab profile already sets enable_load_test_auth = true):
  pip install boto3
  export AWS_PROFILE=lab AWS_REGION=us-east-1
  cd infra && terraform output   # app_url, user_pool_id, user_pool_client_id

Usage:
  python3 scripts/load_test.py setup    --students 300          # create test users + an exam
  python3 scripts/load_test.py run      --label run1-micro      # run both phases
  python3 scripts/load_test.py cleanup                          # delete test users
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import random
import secrets
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request

import boto3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "build", "load-test-state.json")
EVIDENCE = os.path.join(ROOT, "evidence")
DOMAIN = "loadtest.invalid"  # reserved TLD: these addresses can never receive mail


def tf_outputs():
    out = subprocess.run(["terraform", f"-chdir={os.path.join(ROOT, 'infra')}", "output", "-json"],
                         check=True, capture_output=True, text=True).stdout
    return {k: v["value"] for k, v in json.loads(out).items()}


def call(base, method, path, token=None, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, payload = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, payload = e.code, e.read()
    except Exception as e:  # timeouts, resets
        status, payload = 0, str(e).encode()
    return status, (time.perf_counter() - t0) * 1000, payload


def sign_in(idp, pool, client, email, password):
    r = idp.admin_initiate_auth(UserPoolId=pool, ClientId=client, AuthFlow="ADMIN_USER_PASSWORD_AUTH",
                                AuthParameters={"USERNAME": email, "PASSWORD": password})
    return r["AuthenticationResult"]["IdToken"]


def make_user(idp, pool, email, password, group):
    try:
        idp.admin_create_user(UserPoolId=pool, Username=email, MessageAction="SUPPRESS",
                              UserAttributes=[{"Name": "email", "Value": email},
                                              {"Name": "email_verified", "Value": "true"}])
    except idp.exceptions.UsernameExistsException:
        pass
    idp.admin_set_user_password(UserPoolId=pool, Username=email, Password=password, Permanent=True)
    idp.admin_add_user_to_group(UserPoolId=pool, Username=email, GroupName=group)


def setup(args):
    o = tf_outputs()
    pool, client, base = o["user_pool_id"], o["user_pool_client_id"], o["app_url"].rstrip("/")
    idp = boto3.client("cognito-idp")
    password = "Lt-" + secrets.token_urlsafe(12) + "9!"
    tutor = f"tutor@{DOMAIN}"
    make_user(idp, pool, tutor, password, "tutors")
    students = [f"student{i:04d}@{DOMAIN}" for i in range(args.students)]
    with cf.ThreadPoolExecutor(8) as ex:  # Cognito admin APIs are rate-limited; keep this modest
        list(ex.map(lambda e: make_user(idp, pool, e, password, "students"), students))
    now = dt.datetime.now(dt.timezone.utc)
    exam = {
        "title": "Load test exam", "course": "LOAD101", "duration_minutes": 120,
        "opens_at": (now - dt.timedelta(minutes=1)).isoformat(),
        "closes_at": (now + dt.timedelta(hours=6)).isoformat(),
        "questions": [{"id": f"q{i}", "type": "mcq", "text": f"Question {i}", "options": ["A", "B", "C", "D"],
                       "answer": i % 4, "marks": 1} for i in range(1, 31)]
                     + [{"id": "s1", "type": "short", "text": "Explain RPO.", "marks": 5}],
    }
    status, _, payload = call(base, "POST", "/api/exams", sign_in(idp, pool, client, tutor, password), exam)
    if status != 200:
        raise SystemExit(f"creating the exam failed: {status} {payload[:300]!r}")
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({"base": base, "pool": pool, "client": client, "password": password, "tutor": tutor,
               "students": students, "exam_id": json.loads(payload)["id"]}, open(STATE, "w"))
    print(f"created {len(students)} students and exam {json.loads(payload)['id']}; state in {STATE}")


def summarise(name, samples, seconds):
    lat = sorted(s[1] for s in samples)
    codes = {}
    for s in samples:
        codes[s[0]] = codes.get(s[0], 0) + 1
    pct = lambda p: lat[min(len(lat) - 1, int(p / 100 * len(lat)))] if lat else 0
    ok = codes.get(200, 0)
    return {"phase": name, "requests": len(samples), "ok": ok, "error_rate_pct": round(100 * (len(samples) - ok) / max(1, len(samples)), 2),
            "rate_per_s": round(len(samples) / max(seconds, 1e-9), 1), "p50_ms": round(pct(50)), "p95_ms": round(pct(95)),
            "p99_ms": round(pct(99)), "max_ms": round(lat[-1]) if lat else 0,
            "mean_ms": round(statistics.mean(lat)) if lat else 0, "status_codes": codes}


def run(args):
    st = json.load(open(STATE))
    idp = boto3.client("cognito-idp")
    base, exam = st["base"], st["exam_id"]
    print("signing in students ...")
    with cf.ThreadPoolExecutor(8) as ex:
        tokens = list(ex.map(lambda e: sign_in(idp, st["pool"], st["client"], e, st["password"]), st["students"]))
    started_utc = dt.datetime.now(dt.timezone.utc)

    # phase 1: every student starts the exam at a random moment within the window
    samples, lock = [], threading.Lock()

    def start(tok):
        time.sleep(random.uniform(0, args.start_window))
        r = call(base, "POST", f"/api/exams/{exam}/start", tok)
        with lock:
            samples.append(r[:2])

    t0 = time.time()
    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(start, tokens))
    phase1 = summarise("start storm", samples, time.time() - t0)
    print(json.dumps(phase1, indent=2))

    # phase 2: each student autosaves every `interval` seconds
    saves, stop = [], time.time() + args.duration

    def student(tok):
        answers = {}
        time.sleep(random.uniform(0, args.interval))
        while time.time() < stop:
            answers[f"q{random.randint(1, 30)}"] = random.randint(0, 3)
            answers["s1"] = "Recovery point objective " * random.randint(1, 20)
            r = call(base, "PUT", f"/api/exams/{exam}/answers", tok, {"answers": answers})
            with lock:
                saves.append(r[:2])
            time.sleep(max(0, args.interval - r[1] / 1000))

    t0 = time.time()
    with cf.ThreadPoolExecutor(len(tokens)) as ex:
        list(ex.map(student, tokens))
    phase2 = summarise("autosave", saves, time.time() - t0)
    print(json.dumps(phase2, indent=2))

    result = {"label": args.label, "started_utc": started_utc.isoformat(timespec="seconds"),
              "ended_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "students": len(tokens), "start_window_s": args.start_window, "autosave_interval_s": args.interval,
              "phases": [phase1, phase2]}
    os.makedirs(EVIDENCE, exist_ok=True)
    path = os.path.join(EVIDENCE, f"load-test-{args.label}.json")
    json.dump(result, open(path, "w"), indent=2)
    print(f"saved {path}  - now screenshot CloudWatch for {result['started_utc']} to {result['ended_utc']}")


def cleanup(args):
    st = json.load(open(STATE))
    idp = boto3.client("cognito-idp")
    for e in st["students"] + [st["tutor"]]:
        try:
            idp.admin_delete_user(UserPoolId=st["pool"], Username=e)
        except idp.exceptions.UserNotFoundException:
            pass
    print("test users deleted")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup"); s.add_argument("--students", type=int, default=300)
    r = sub.add_parser("run")
    r.add_argument("--label", default="run1")
    r.add_argument("--start-window", type=float, default=30, help="seconds over which all students start")
    r.add_argument("--interval", type=float, default=3, help="seconds between autosaves per student")
    r.add_argument("--duration", type=float, default=300, help="seconds of autosave load")
    r.add_argument("--workers", type=int, default=100)
    sub.add_parser("cleanup")
    a = ap.parse_args()
    {"setup": setup, "run": run, "cleanup": cleanup}[a.cmd](a)
