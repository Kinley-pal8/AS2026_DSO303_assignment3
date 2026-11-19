"""SQS worker: auto-marks MCQs of a submitted attempt and stores the result in PostgreSQL.

Idempotent: re-processing the same attempt overwrites the (unreleased) result with the same values.
"""
import json
import logging
import os

import boto3

import core
import db

log = logging.getLogger()
log.setLevel(logging.INFO)
TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def handler(event, context):
    failures = []
    for record in event["Records"]:
        try:
            mark_attempt(json.loads(record["body"])["attempt_id"])
        except Exception:
            log.exception("marking failed for message %s", record["messageId"])
            failures.append({"itemIdentifier": record["messageId"]})
    # Only failed messages return to the queue (and to the DLQ after 5 tries).
    return {"batchItemFailures": failures}


def mark_attempt(aid):
    item = TABLE.get_item(Key={"attempt_id": aid}, ConsistentRead=True).get("Item")
    if not item or item.get("attempt_status") != "SUBMITTED":
        log.warning("attempt %s not found or not submitted; skipping", aid)
        return
    item = core.normalize(item)
    exam = db.query("SELECT questions FROM exams WHERE id = CAST(:id AS uuid)", id=item["exam_id"])
    if not exam:
        log.error("exam %s missing for attempt %s", item["exam_id"], aid)
        return
    answers = item.get("answers") or {}
    score = core.mark(exam[0]["questions"], answers)
    db.query(
        "INSERT INTO results (exam_id, student_id, student_email, mcq_score, mcq_max, sa_max, answers) "
        "VALUES (CAST(:e AS uuid), :s, :em, :ms, :mm, :sm, CAST(:a AS jsonb)) "
        "ON CONFLICT (exam_id, student_id) DO UPDATE SET mcq_score = EXCLUDED.mcq_score, "
        "mcq_max = EXCLUDED.mcq_max, sa_max = EXCLUDED.sa_max, answers = EXCLUDED.answers, marked_at = now() "
        "WHERE NOT results.released",
        e=item["exam_id"], s=item["student_id"], em=item.get("student_email") or "",
        ms=score["mcq_score"], mm=score["mcq_max"], sm=score["sa_max"], a=json.dumps(answers),
    )
    log.info(json.dumps({"event": "marked", "attempt_id": aid, **score}))
