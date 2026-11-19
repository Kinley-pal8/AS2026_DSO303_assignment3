"""Enqueue e-mails onto the notifications queue (sent asynchronously by notifier.py)."""
import json
import os
import uuid

import boto3

_sqs = boto3.client("sqs")


def enqueue(messages):
    """messages: list of {"to", "subject", "body"}. Sent in batches of 10."""
    queue = os.environ["NOTIFY_QUEUE_URL"]
    for i in range(0, len(messages), 10):
        chunk = messages[i:i + 10]
        res = _sqs.send_message_batch(
            QueueUrl=queue,
            Entries=[{"Id": str(uuid.uuid4()), "MessageBody": json.dumps(m)} for m in chunk],
        )
        if res.get("Failed"):
            raise RuntimeError(f"failed to enqueue {len(res['Failed'])} notifications")
