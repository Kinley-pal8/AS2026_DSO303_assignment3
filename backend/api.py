"""API Lambda behind API Gateway HTTP API (JWT authorizer = Cognito). Routes are /api/*."""
import base64
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

import core
import db
import notify

log = logging.getLogger()
log.setLevel(logging.INFO)

REGION = os.environ["AWS_REGION"]
GRACE = int(os.environ.get("GRACE_SECONDS", "60"))
BUCKET = os.environ["UPLOAD_BUCKET"]
ORIGIN_SECRET = os.environ.get("ORIGIN_SECRET", "")
TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
SQS = boto3.client("sqs")
COGNITO = boto3.client("cognito-idp")
# Regional virtual-hosted endpoint so browser uploads never hit a 307 redirect (breaks CORS).
S3 = boto3.client(
    "s3", region_name=REGION, endpoint_url=f"https://s3.{REGION}.amazonaws.com",
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)

# Provisioned-concurrency environments are prepared before the exam opens. Opening the database
# connection here, during that warm-up, saves the ~0.3 s the first student request would otherwise
# spend on it (load test run 1). On-demand cold starts keep connecting on the first request.
if os.environ.get("AWS_LAMBDA_INITIALIZATION_TYPE") == "provisioned-concurrency":
    try:
        db.query("SELECT 1 AS ok")
    except Exception as e:  # never fail the warm-up; query() connects again on first use
        log.warning("db warm-up failed (%s); connecting on first request", e)

STAFF = {"tutors", "admins"}
STUDENT = {"students"}
ADMIN = {"admins"}
_exam_cache = {}  # exam_id -> (expires_epoch, row); absorbs the 3,000-student exam-start burst
ROUTES = []


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def route(method, pattern, roles=None):
    def deco(fn):
        ROUTES.append((method, re.compile(f"^{pattern}$"), roles, fn))
        return fn
    return deco


def _json_default(o):
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    if isinstance(o, datetime):
        return o.isoformat()
    if isinstance(o, uuid.UUID):
        return str(o)
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(type(o).__name__)


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
        "body": json.dumps(body, default=_json_default),
    }


def handler(event, context):
    headers = event.get("headers") or {}
    # Only accept traffic that came through CloudFront (+WAF), not the raw execute-api URL.
    if ORIGIN_SECRET and headers.get("x-origin-verify") != ORIGIN_SECRET:
        return respond(403, {"error": "forbidden"})
    method = event["requestContext"]["http"]["method"]
    path = event.get("rawPath", "")
    if path == "/api/health":
        if (event.get("queryStringParameters") or {}).get("deep"):
            try:  # used by scripts/simulate-az-failover.sh to time an RDS failover
                db.query("SELECT 1 AS ok")
            except Exception as e:
                return respond(503, {"ok": False, "db": type(e).__name__, "time": int(time.time())})
            return respond(200, {"ok": True, "db": "ok", "az": os.environ.get("AWS_AVAILABILITY_ZONE"), "time": int(time.time())})
        return respond(200, {"ok": True, "time": int(time.time())})

    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    user = {
        "sub": claims.get("sub"),
        "email": claims.get("email"),
        "name": claims.get("name") or claims.get("email"),
        "groups": core.parse_groups(claims.get("cognito:groups")),
    }
    if not user["sub"]:
        return respond(401, {"error": "unauthenticated"})

    try:
        raw = event.get("body") or ""
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode()
        if len(raw) > 256 * 1024:
            raise HttpError(413, "request body too large")
        body = json.loads(raw) if raw else {}
        if not isinstance(body, dict):
            raise HttpError(400, "body must be a JSON object")
        for m, rx, roles, fn in ROUTES:
            match = rx.match(path)
            if m == method and match:
                if roles and not roles & set(user["groups"]):
                    raise HttpError(403, "your role cannot perform this action")
                return respond(200, fn(user, body, **match.groupdict()))
        raise HttpError(404, "not found")
    except HttpError as e:
        return respond(e.status, {"error": str(e)})
    except (ValueError, json.JSONDecodeError) as e:
        return respond(400, {"error": str(e)})
    except Exception:
        log.exception("unhandled error")
        return respond(500, {"error": "internal error"})


# ------------------------------------------------------------------ helpers
def is_staff(user):
    return bool(STAFF & set(user["groups"]))


def now_utc():
    return datetime.now(timezone.utc)


def load_exam(exam_id, cached=True):
    if not core.is_uuid(exam_id):
        raise HttpError(404, "exam not found")
    hit = _exam_cache.get(exam_id)
    if cached and hit and hit[0] > time.time():
        return hit[1]
    rows = db.query("SELECT * FROM exams WHERE id = CAST(:id AS uuid)", id=exam_id)
    if not rows:
        raise HttpError(404, "exam not found")
    _exam_cache[exam_id] = (time.time() + 60, rows[0])
    return rows[0]


def attempt_id(exam_id, sub):
    return f"{exam_id}#{sub}"


def public_attempt(item):
    item = core.normalize(item)
    return {k: item.get(k) for k in ("attempt_status", "started_at", "deadline_epoch", "saved_at", "answers")}


def req_str(body, key, max_len=200):
    value = body.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > max_len:
        raise HttpError(400, f"{key} is required (max {max_len} chars)")
    return value.strip()


# ------------------------------------------------------------------ common
@route("GET", "/api/me")
def me(user, body):
    return user


# ------------------------------------------------------------------ exams
@route("GET", "/api/exams")
def list_exams(user, body):
    rows = db.query(
        "SELECT id, title, course, duration_minutes, opens_at, closes_at, created_by "
        "FROM exams WHERE closes_at > now() - interval '60 days' ORDER BY opens_at DESC LIMIT 200"
    )
    if not is_staff(user) and rows:
        keys = [{"attempt_id": attempt_id(str(r["id"]), user["sub"])} for r in rows[:100]]
        res = boto3.resource("dynamodb").batch_get_item(RequestItems={
            TABLE.name: {"Keys": keys, "ProjectionExpression": "attempt_id, attempt_status"}
        })
        status = {i["attempt_id"]: i["attempt_status"] for i in res["Responses"].get(TABLE.name, [])}
        for r in rows:
            r["attempt_status"] = status.get(attempt_id(str(r["id"]), user["sub"]))
    return {"exams": rows}


@route("POST", "/api/exams", STAFF)
def create_exam(user, body):
    title, course = req_str(body, "title"), req_str(body, "course", 50)
    duration = body.get("duration_minutes")
    if not isinstance(duration, int) or not 1 <= duration <= 600:
        raise HttpError(400, "duration_minutes must be 1-600")
    opens, closes = core.parse_iso(body.get("opens_at")), core.parse_iso(body.get("closes_at"))
    if closes <= opens:
        raise HttpError(400, "closes_at must be after opens_at")
    questions = core.validate_questions(body.get("questions"))
    exam_id = str(uuid.uuid4())
    db.query(
        "INSERT INTO exams (id, title, course, duration_minutes, opens_at, closes_at, questions, created_by) "
        "VALUES (CAST(:id AS uuid), :t, :c, :d, :o, :cl, CAST(:q AS jsonb), :by)",
        id=exam_id, t=title, c=course, d=duration, o=opens, cl=closes,
        q=json.dumps(questions), by=user["email"],
    )
    return {"id": exam_id}


@route("GET", "/api/exams/(?P<exam_id>[0-9a-f-]{36})")
def get_exam(user, body, exam_id):
    exam = load_exam(exam_id, cached=False)
    if is_staff(user):
        return exam
    return {k: v for k, v in exam.items() if k != "questions"}


@route("POST", "/api/exams/(?P<exam_id>[0-9a-f-]{36})/start", STUDENT)
def start_exam(user, body, exam_id):
    exam = load_exam(exam_id)
    now = now_utc()
    if now < exam["opens_at"] or now > exam["closes_at"]:
        raise HttpError(409, "this exam is not open")
    deadline = min(now + timedelta(minutes=exam["duration_minutes"]), exam["closes_at"])
    item = {
        "attempt_id": attempt_id(exam_id, user["sub"]),
        "exam_id": exam_id,
        "student_id": user["sub"],
        "student_email": user["email"],
        "attempt_status": "IN_PROGRESS",
        "open_status": "OPEN",  # sparse GSI key used by the sweeper to auto-submit
        "started_at": int(now.timestamp()),
        "deadline_epoch": int(deadline.timestamp()),
        "saved_at": 0,
        "answers": {},
    }
    try:
        TABLE.put_item(Item=item, ConditionExpression="attribute_not_exists(attempt_id)")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        item = TABLE.get_item(Key={"attempt_id": item["attempt_id"]}, ConsistentRead=True)["Item"]
    return {
        "attempt": public_attempt(item),
        "paper": {"title": exam["title"], "course": exam["course"], "questions": core.public_paper(exam["questions"])},
        "server_time": int(time.time()),
    }


def _save_answers(user, exam_id, answers):
    exam = load_exam(exam_id)
    clean = core.validate_answers(answers, exam["questions"])
    now = int(time.time())
    try:
        TABLE.update_item(
            Key={"attempt_id": attempt_id(exam_id, user["sub"])},
            UpdateExpression="SET answers = :a, saved_at = :n ADD save_count :one",
            ConditionExpression="attempt_status = :ip AND deadline_epoch >= :cutoff",
            ExpressionAttributeValues={":a": clean, ":n": now, ":one": 1, ":ip": "IN_PROGRESS", ":cutoff": now - GRACE},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HttpError(409, "attempt is closed, submitted or not started")
        raise
    return now


@route("PUT", "/api/exams/(?P<exam_id>[0-9a-f-]{36})/answers", STUDENT)
def autosave(user, body, exam_id):
    return {"saved_at": _save_answers(user, exam_id, body.get("answers"))}


@route("POST", "/api/exams/(?P<exam_id>[0-9a-f-]{36})/submit", STUDENT)
def submit_exam(user, body, exam_id):
    aid = attempt_id(exam_id, user["sub"])
    if "answers" in body:
        try:
            _save_answers(user, exam_id, body["answers"])
        except HttpError:
            pass  # past deadline: the last autosave stands
    now = int(time.time())
    try:
        TABLE.update_item(
            Key={"attempt_id": aid},
            UpdateExpression="SET attempt_status = :s, submitted_at = :n REMOVE open_status",
            ConditionExpression="attempt_status = :ip",
            ExpressionAttributeValues={":s": "SUBMITTED", ":n": now, ":ip": "IN_PROGRESS"},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        item = TABLE.get_item(Key={"attempt_id": aid}, ConsistentRead=True).get("Item")
        if not item:
            raise HttpError(409, "exam not started")
        # Already submitted: re-enqueue anyway (marking is idempotent) so a lost message self-heals.
    SQS.send_message(QueueUrl=os.environ["MARKING_QUEUE_URL"], MessageBody=json.dumps({"attempt_id": aid}))
    return {"status": "SUBMITTED"}


@route("GET", "/api/exams/(?P<exam_id>[0-9a-f-]{36})/results", STAFF)
def exam_results(user, body, exam_id):
    load_exam(exam_id)
    rows = db.query(
        "SELECT student_id, student_email, mcq_score, mcq_max, sa_score, sa_max, answers, released, marked_at "
        "FROM results WHERE exam_id = CAST(:id AS uuid) ORDER BY student_email", id=exam_id,
    )
    return {"results": rows}


@route("POST", "/api/exams/(?P<exam_id>[0-9a-f-]{36})/marks", STAFF)
def mark_short_answers(user, body, exam_id):
    student_id = req_str(body, "student_id", 64)
    score = body.get("sa_score")
    if not isinstance(score, (int, float)) or isinstance(score, bool) or score < 0:
        raise HttpError(400, "sa_score must be a non-negative number")
    rows = db.query(
        "UPDATE results SET sa_score = :s WHERE exam_id = CAST(:id AS uuid) AND student_id = :st "
        "AND NOT released AND :s <= sa_max RETURNING student_id",
        s=Decimal(str(score)), id=exam_id, st=student_id,
    )
    if not rows:
        raise HttpError(409, "result not found, already released, or score above maximum")
    return {"ok": True}


@route("POST", "/api/exams/(?P<exam_id>[0-9a-f-]{36})/release", STAFF)
def release_results(user, body, exam_id):
    exam = load_exam(exam_id)
    rows = db.query(
        "UPDATE results SET released = true, released_at = now() WHERE exam_id = CAST(:id AS uuid) "
        "AND NOT released AND (sa_max = 0 OR sa_score IS NOT NULL) "
        "RETURNING student_email, mcq_score, mcq_max, sa_score, sa_max", id=exam_id,
    )
    pending = db.query(
        "SELECT count(*) AS n FROM results WHERE exam_id = CAST(:id AS uuid) AND NOT released", id=exam_id,
    )[0]["n"]
    app_url = os.environ.get("APP_URL", "")
    notify.enqueue([{
        "to": r["student_email"],
        "subject": f"Result released: {exam['title']}",
        "body": (f"Your result for {exam['title']} ({exam['course']}) is now available.\n"
                 f"Score: {r['mcq_score'] + (r['sa_score'] or 0)} / {r['mcq_max'] + r['sa_max']}\n\n"
                 f"View it at {app_url}"),
    } for r in rows])
    return {"released": len(rows), "still_pending": pending}


@route("GET", "/api/results", STUDENT)
def my_results(user, body):
    rows = db.query(
        "SELECT r.exam_id, e.title, e.course, r.mcq_score, r.mcq_max, r.sa_score, r.sa_max, r.released_at "
        "FROM results r JOIN exams e ON e.id = r.exam_id WHERE r.student_id = :sub AND r.released "
        "ORDER BY r.released_at DESC", sub=user["sub"],
    )
    return {"results": rows}


# ------------------------------------------------------------------ assignments
@route("GET", "/api/assignments")
def list_assignments(user, body):
    rows = db.query(
        "SELECT a.id, a.title, a.course, a.due_at, a.tutor_email, "
        "(SELECT max(s.submitted_at) FROM submissions s WHERE s.assignment_id = a.id AND s.student_id = :sub) "
        "AS my_last_submission, "
        "(SELECT count(*) FROM submissions s WHERE s.assignment_id = a.id) AS submission_count "
        "FROM assignments a ORDER BY a.due_at DESC LIMIT 200", sub=user["sub"],
    )
    return {"assignments": rows}


@route("POST", "/api/assignments", STAFF)
def create_assignment(user, body):
    title, course = req_str(body, "title"), req_str(body, "course", 50)
    due = core.parse_iso(body.get("due_at"))
    tutor_email = (body.get("tutor_email") or user["email"]).strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", tutor_email):
        raise HttpError(400, "tutor_email is invalid")
    aid = str(uuid.uuid4())
    db.query(
        "INSERT INTO assignments (id, title, course, due_at, tutor_email, created_by) "
        "VALUES (CAST(:id AS uuid), :t, :c, :d, :te, :by)",
        id=aid, t=title, c=course, d=due, te=tutor_email, by=user["email"],
    )
    return {"id": aid}


@route("POST", "/api/assignments/(?P<assignment_id>[0-9a-f-]{36})/upload-url", STUDENT)
def upload_url(user, body, assignment_id):
    if not db.query("SELECT 1 AS ok FROM assignments WHERE id = CAST(:id AS uuid)", id=assignment_id):
        raise HttpError(404, "assignment not found")
    size = body.get("size")
    if not isinstance(size, int) or not 0 < size <= core.MAX_UPLOAD_BYTES:
        raise HttpError(400, "file must be between 1 byte and 50 MB")
    filename = core.sanitize_filename(body.get("filename"))
    key = core.build_upload_key(assignment_id, user["sub"], filename)
    ctype = core.content_type_for(filename)
    meta = {"x-amz-meta-student-email": user["email"] or ""}
    post = S3.generate_presigned_post(
        Bucket=BUCKET, Key=key,
        Fields={"Content-Type": ctype, **meta},
        Conditions=[["content-length-range", 1, core.MAX_UPLOAD_BYTES], {"Content-Type": ctype},
                    *({k: v} for k, v in meta.items())],
        ExpiresIn=900,
    )
    return {"url": post["url"], "fields": post["fields"], "key": key, "max_bytes": core.MAX_UPLOAD_BYTES}


@route("GET", "/api/assignments/(?P<assignment_id>[0-9a-f-]{36})/submissions", STAFF)
def list_submissions(user, body, assignment_id):
    rows = db.query(
        "SELECT id, student_email, filename, size_bytes, late, submitted_at, s3_key FROM submissions "
        "WHERE assignment_id = CAST(:id AS uuid) ORDER BY submitted_at DESC", id=assignment_id,
    )
    for r in rows:
        r["download_url"] = S3.generate_presigned_url(
            "get_object", ExpiresIn=300,
            Params={"Bucket": BUCKET, "Key": r.pop("s3_key"),
                    "ResponseContentDisposition": f'attachment; filename="{r["filename"]}"'},
        )
    return {"submissions": rows}


# ------------------------------------------------------------------ admin
@route("GET", "/api/admin/users", ADMIN)
def list_users(user, body):
    pool = os.environ["USER_POOL_ID"]
    users = []
    for group in core.ROLES:
        kwargs = {"UserPoolId": pool, "GroupName": group, "Limit": 60}
        while len(users) < 1000:
            page = COGNITO.list_users_in_group(**kwargs)
            for u in page["Users"]:
                attrs = {a["Name"]: a["Value"] for a in u.get("Attributes", [])}
                users.append({"email": attrs.get("email"), "name": attrs.get("name"),
                              "role": group, "status": u["UserStatus"], "enabled": u["Enabled"]})
            if "NextToken" not in page:
                break
            kwargs["NextToken"] = page["NextToken"]
    return {"users": users}


@route("POST", "/api/admin/users", ADMIN)
def create_user(user, body):
    email, role = req_str(body, "email", 254).lower(), body.get("role")
    name = (body.get("name") or email).strip()[:100]
    if role not in core.ROLES:
        raise HttpError(400, f"role must be one of {', '.join(core.ROLES)}")
    pool = os.environ["USER_POOL_ID"]
    try:
        COGNITO.admin_create_user(
            UserPoolId=pool, Username=email, DesiredDeliveryMediums=["EMAIL"],
            UserAttributes=[{"Name": "email", "Value": email}, {"Name": "email_verified", "Value": "true"},
                            {"Name": "name", "Value": name}],
        )
    except COGNITO.exceptions.UsernameExistsException:
        pass
    COGNITO.admin_add_user_to_group(UserPoolId=pool, Username=email, GroupName=role)
    return {"email": email, "role": role}
