"""PostgreSQL access: through RDS Proxy with IAM tokens, or directly with the Secrets Manager password.

No password is ever stored in code or environment variables.
"""
import json
import logging
import os
import ssl

import boto3
import pg8000.native

log = logging.getLogger(__name__)
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS exams (
  id               UUID PRIMARY KEY,
  title            TEXT NOT NULL,
  course           TEXT NOT NULL,
  duration_minutes INT  NOT NULL CHECK (duration_minutes BETWEEN 1 AND 600),
  opens_at         TIMESTAMPTZ NOT NULL,
  closes_at        TIMESTAMPTZ NOT NULL,
  questions        JSONB NOT NULL,
  created_by       TEXT NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (closes_at > opens_at)
);
CREATE TABLE IF NOT EXISTS results (
  exam_id       UUID NOT NULL REFERENCES exams(id),
  student_id    TEXT NOT NULL,
  student_email TEXT NOT NULL,
  mcq_score     NUMERIC NOT NULL,
  mcq_max       NUMERIC NOT NULL,
  sa_score      NUMERIC,
  sa_max        NUMERIC NOT NULL,
  answers       JSONB NOT NULL,
  released      BOOLEAN NOT NULL DEFAULT false,
  marked_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  released_at   TIMESTAMPTZ,
  PRIMARY KEY (exam_id, student_id)
);
CREATE INDEX IF NOT EXISTS results_student_idx ON results (student_id);
CREATE TABLE IF NOT EXISTS assignments (
  id          UUID PRIMARY KEY,
  title       TEXT NOT NULL,
  course      TEXT NOT NULL,
  due_at      TIMESTAMPTZ NOT NULL,
  tutor_email TEXT NOT NULL,
  created_by  TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS submissions (
  id            UUID PRIMARY KEY,
  assignment_id UUID NOT NULL REFERENCES assignments(id),
  student_id    TEXT NOT NULL,
  student_email TEXT NOT NULL,
  s3_key        TEXT NOT NULL UNIQUE,
  filename      TEXT NOT NULL,
  size_bytes    BIGINT NOT NULL,
  late          BOOLEAN NOT NULL,
  submitted_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS submissions_assignment_idx ON submissions (assignment_id, student_id);
"""


_RDS_CA = os.path.join(os.path.dirname(__file__), "rds-global-bundle.pem")


def _ssl_context():
    ctx = ssl.create_default_context()  # trusts RDS Proxy (Amazon Trust Services certs)
    if os.path.exists(_RDS_CA):
        ctx.load_verify_locations(_RDS_CA)  # trusts direct RDS connections (RDS CA)
    return ctx


def _credentials(host, port):
    """DB_AUTH=iam: short-lived IAM token for RDS Proxy. DB_AUTH=secret: RDS-managed password."""
    if os.environ.get("DB_AUTH", "iam") == "secret":
        secret = json.loads(boto3.client("secretsmanager").get_secret_value(
            SecretId=os.environ["DB_SECRET_ARN"])["SecretString"])
        return secret["username"], secret["password"]
    user = os.environ["DB_USER"]
    token = boto3.client("rds").generate_db_auth_token(
        DBHostname=host, Port=port, DBUsername=user, Region=os.environ["AWS_REGION"]
    )
    return user, token


def _connect():
    host = os.environ["DB_HOST"]
    port = int(os.environ.get("DB_PORT", "5432"))
    user, password = _credentials(host, port)
    conn = pg8000.native.Connection(
        user=user, host=host, port=port, database=os.environ["DB_NAME"],
        password=password, ssl_context=_ssl_context(), timeout=10,
    )
    # Advisory lock so concurrent cold starts don't race creating the schema.
    conn.run("BEGIN")
    conn.run("SELECT pg_advisory_xact_lock(4242)")
    for stmt in filter(None, (s.strip() for s in SCHEMA.split(";"))):
        conn.run(stmt)
    conn.run("COMMIT")
    return conn


def _get():
    global _conn
    if _conn is None:
        _conn = _connect()
    return _conn


def query(sql, **params):
    """Run SQL and return rows as dicts. Reconnects once if the pooled connection died."""
    global _conn
    for attempt in (1, 2):
        conn = _get()
        try:
            rows = conn.run(sql, **params)
            if not conn.columns:
                return []
            names = [c["name"] for c in conn.columns]
            return [dict(zip(names, r)) for r in rows]
        except (pg8000.native.InterfaceError, OSError) as exc:
            log.warning("db connection lost (%s), reconnecting", exc)
            _conn = None
            if attempt == 2:
                raise
