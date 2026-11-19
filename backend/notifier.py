"""SQS worker: sends e-mails with Amazon SES."""
import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

log = logging.getLogger()
log.setLevel(logging.INFO)
SES = boto3.client("sesv2")
PERMANENT = {"MessageRejected", "BadRequestException", "NotFoundException", "MailFromDomainNotVerifiedException"}


def handler(event, context):
    failures = []
    for record in event["Records"]:
        msg = json.loads(record["body"])
        if os.environ.get("EMAIL_MODE", "ses") == "log":
            # Where SES is unavailable (e.g. AWS Academy Learner Lab) the e-mail is written to
            # CloudWatch Logs so the async flow can still be demonstrated end to end.
            log.info(json.dumps({"event": "email_logged", "to": msg["to"], "subject": msg["subject"],
                                 "body": msg["body"]}))
            continue
        try:
            SES.send_email(
                FromEmailAddress=os.environ["SENDER_EMAIL"],
                Destination={"ToAddresses": [msg["to"]]},
                Content={"Simple": {"Subject": {"Data": msg["subject"][:200]},
                                    "Body": {"Text": {"Data": msg["body"]}}}},
            )
            log.info(json.dumps({"event": "email_sent", "subject": msg["subject"]}))
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in PERMANENT:
                # e.g. unverified recipient while SES is in sandbox: retrying will not help.
                log.error("permanent SES failure (%s) for message %s: %s", code, record["messageId"], e)
            else:
                log.warning("transient SES failure (%s); will retry", code)
                failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}
