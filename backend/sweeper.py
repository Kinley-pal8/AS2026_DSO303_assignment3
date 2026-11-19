"""Runs every minute (EventBridge). Auto-submits attempts whose time ran out so they still get marked."""
import json
import logging
import os
import time

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

log = logging.getLogger()
log.setLevel(logging.INFO)
TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
SQS = boto3.client("sqs")
GRACE = int(os.environ.get("GRACE_SECONDS", "60"))


def handler(event, context):
    cutoff = int(time.time()) - GRACE
    kwargs = {
        "IndexName": "open-by-deadline",
        "KeyConditionExpression": Key("open_status").eq("OPEN") & Key("deadline_epoch").lt(cutoff),
    }
    closed = 0
    while True:
        page = TABLE.query(**kwargs)
        for item in page["Items"]:
            try:
                TABLE.update_item(
                    Key={"attempt_id": item["attempt_id"]},
                    UpdateExpression="SET attempt_status = :s, submitted_at = :n, auto_submitted = :t REMOVE open_status",
                    ConditionExpression="attempt_status = :ip",
                    ExpressionAttributeValues={":s": "SUBMITTED", ":n": int(time.time()), ":t": True, ":ip": "IN_PROGRESS"},
                )
            except ClientError as e:
                if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise
            SQS.send_message(QueueUrl=os.environ["MARKING_QUEUE_URL"],
                             MessageBody=json.dumps({"attempt_id": item["attempt_id"]}))
            closed += 1
        if "LastEvaluatedKey" not in page or context.get_remaining_time_in_millis() < 5000:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    log.info(json.dumps({"event": "sweep", "auto_submitted": closed}))
    return {"auto_submitted": closed}
