"""Pure business logic (no AWS calls) so it can be unit-tested in CI."""
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_UPLOADS = {".pdf": "application/pdf", ".zip": "application/zip"}
ROLES = ("students", "tutors", "admins")
_QID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MAX_SHORT_ANSWER = 5000


def is_uuid(value):
    return isinstance(value, str) and bool(_UUID.match(value))


def parse_groups(claim):
    """HTTP API JWT authorizer renders array claims as '[a b]' strings."""
    if not claim:
        return []
    if isinstance(claim, list):
        return [g for g in claim if g in ROLES]
    parts = re.split(r"[\s,]+", str(claim).strip("[]"))
    return [g for g in parts if g in ROLES]


def parse_iso(value):
    """Parse an ISO-8601 timestamp; naive values are treated as UTC."""
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- exams
def validate_questions(questions):
    if not isinstance(questions, list) or not 1 <= len(questions) <= 200:
        raise ValueError("questions must be a list of 1-200 items")
    seen, clean = set(), []
    for q in questions:
        if not isinstance(q, dict):
            raise ValueError("each question must be an object")
        qid, qtype, text = q.get("id"), q.get("type"), q.get("text")
        if not isinstance(qid, str) or not _QID.match(qid) or qid in seen:
            raise ValueError(f"invalid or duplicate question id: {qid!r}")
        seen.add(qid)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{qid}: text is required")
        marks = q.get("marks", 1)
        if not isinstance(marks, int) or not 1 <= marks <= 100:
            raise ValueError(f"{qid}: marks must be an integer 1-100")
        item = {"id": qid, "type": qtype, "text": text.strip(), "marks": marks}
        if qtype == "mcq":
            options = q.get("options")
            if not isinstance(options, list) or not 2 <= len(options) <= 10 or not all(isinstance(o, str) for o in options):
                raise ValueError(f"{qid}: mcq needs 2-10 string options")
            answer = q.get("answer")
            if not isinstance(answer, int) or not 0 <= answer < len(options):
                raise ValueError(f"{qid}: answer must be the index of the correct option")
            item.update(options=options, answer=answer)
        elif qtype != "short":
            raise ValueError(f"{qid}: type must be 'mcq' or 'short'")
        clean.append(item)
    return clean


def public_paper(questions):
    """The paper a student sees: correct answers removed."""
    return [{k: v for k, v in q.items() if k != "answer"} for q in questions]


def validate_answers(answers, questions=None):
    if not isinstance(answers, dict) or len(answers) > 200:
        raise ValueError("answers must be an object with at most 200 entries")
    allowed = {q["id"]: q["type"] for q in questions} if questions else None
    clean = {}
    for qid, value in answers.items():
        if not _QID.match(str(qid)):
            raise ValueError(f"invalid question id {qid!r}")
        if allowed is not None and qid not in allowed:
            continue
        if isinstance(value, bool):
            raise ValueError(f"{qid}: invalid answer")
        if isinstance(value, int) and 0 <= value < 10:
            clean[qid] = value
        elif isinstance(value, str) and len(value) <= MAX_SHORT_ANSWER:
            clean[qid] = value
        elif value is None:
            continue
        else:
            raise ValueError(f"{qid}: answer must be an option index or text up to {MAX_SHORT_ANSWER} chars")
    return clean


def normalize(value):
    """Convert DynamoDB Decimals back to ints/floats recursively."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


def mark(questions, answers):
    """Auto-mark MCQs. Short answers are left for the tutor."""
    mcq_score = mcq_max = sa_max = 0
    for q in questions:
        if q["type"] == "mcq":
            mcq_max += q["marks"]
            given = answers.get(q["id"])
            if isinstance(given, int) and not isinstance(given, bool) and given == q["answer"]:
                mcq_score += q["marks"]
        else:
            sa_max += q["marks"]
    return {"mcq_score": mcq_score, "mcq_max": mcq_max, "sa_max": sa_max}


# ---------------------------------------------------------------- uploads
def sanitize_filename(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("filename is required")
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    stem, dot, ext = base.rpartition(".")
    ext = f".{ext.lower()}" if dot else ""
    if ext not in ALLOWED_UPLOADS:
        raise ValueError("only .pdf and .zip files are accepted")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "file"
    return stem[:80] + ext


def content_type_for(filename):
    return ALLOWED_UPLOADS[filename[filename.rfind("."):].lower()]


def build_upload_key(assignment_id, student_id, filename):
    if not is_uuid(assignment_id):
        raise ValueError("invalid assignment id")
    if not re.match(r"^[A-Za-z0-9-]{1,64}$", student_id or ""):
        raise ValueError("invalid student id")
    return f"submissions/{assignment_id}/{student_id}/{uuid.uuid4()}-{sanitize_filename(filename)}"


def parse_upload_key(key):
    m = re.match(r"^submissions/([0-9a-f-]{36})/([A-Za-z0-9-]{1,64})/([0-9a-f-]{36})-(.+)$", key or "")
    if not m or not is_uuid(m.group(1)):
        return None
    return {"assignment_id": m.group(1), "student_id": m.group(2), "filename": m.group(4)}


def sniff_ok(first_bytes, filename):
    """Check magic bytes match the claimed extension (PDF '%PDF', ZIP 'PK')."""
    if filename.lower().endswith(".pdf"):
        return first_bytes.startswith(b"%PDF")
    if filename.lower().endswith(".zip"):
        return first_bytes[:4] in (b"PK\x03\x04", b"PK\x05\x06")
    return False
