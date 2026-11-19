"""SQS worker for S3 ObjectCreated events: validates an assignment upload, records it, notifies the tutor."""
import json
import logging
import os
import uuid
from urllib.parse import unquote_plus

import boto3

import core
import db
import notify

log = logging.getLogger()
log.setLevel(logging.INFO)
S3 = boto3.client("s3")


def handler(event, context):
    failures = []
    for record in event["Records"]:
        try:
            body = json.loads(record["body"])
            for s3rec in body.get("Records", []):  # s3:TestEvent has no Records
                process(s3rec["s3"]["bucket"]["name"], unquote_plus(s3rec["s3"]["object"]["key"]))
        except Exception:
            log.exception("upload processing failed for message %s", record["messageId"])
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}


def reject(bucket, key, email, reason):
    log.warning("rejecting %s: %s", key, reason)
    S3.put_object_tagging(Bucket=bucket, Key=key, Tagging={"TagSet": [{"Key": "status", "Value": "rejected"}]})
    if email:
        notify.enqueue([{"to": email, "subject": "Assignment upload rejected",
                         "body": f"Your upload could not be accepted: {reason}. Please upload a valid PDF or ZIP."}])


def process(bucket, key):
    parsed = core.parse_upload_key(key)
    if not parsed:
        log.warning("ignoring unexpected key %s", key)
        return
    head = S3.head_object(Bucket=bucket, Key=key)
    size = head["ContentLength"]
    email = head.get("Metadata", {}).get("student-email", "")
    if size > core.MAX_UPLOAD_BYTES:
        return reject(bucket, key, email, "file is larger than 50 MB")
    first = S3.get_object(Bucket=bucket, Key=key, Range="bytes=0-7")["Body"].read()
    if not core.sniff_ok(first, parsed["filename"]):
        return reject(bucket, key, email, "file content does not match its .pdf/.zip extension")

    rows = db.query(
        "INSERT INTO submissions (id, assignment_id, student_id, student_email, s3_key, filename, size_bytes, late) "
        "SELECT CAST(:id AS uuid), a.id, :st, :em, :k, :fn, :sz, now() > a.due_at "
        "FROM assignments a WHERE a.id = CAST(:aid AS uuid) "
        "ON CONFLICT (s3_key) DO NOTHING RETURNING late",
        id=str(uuid.uuid4()), aid=parsed["assignment_id"], st=parsed["student_id"], em=email,
        k=key, fn=parsed["filename"], sz=size,
    )
    if not rows:  # duplicate event (S3 is at-least-once) or unknown assignment
        log.info("submission %s already recorded or assignment missing", key)
        return
    late = rows[0]["late"]
    a = db.query("SELECT title, tutor_email FROM assignments WHERE id = CAST(:id AS uuid)", id=parsed["assignment_id"])[0]
    mb = f"{size / 1024 / 1024:.1f} MB"
    msgs = [{"to": a["tutor_email"], "subject": f"New submission: {a['title']}",
             "body": f"{email} submitted {parsed['filename']} ({mb}){' LATE' if late else ''} for {a['title']}.\n"
                     f"Open {os.environ.get('APP_URL', '')} to download it."}]
    if email:
        msgs.append({"to": email, "subject": f"Receipt: {a['title']}",
                     "body": f"We received {parsed['filename']} ({mb}) for {a['title']}."
                             f"{' Note: this was after the due date.' if late else ''}"})
    notify.enqueue(msgs)
    log.info(json.dumps({"event": "submission_recorded", "key": key, "size": size, "late": late}))
