# Failure tests

There are four scenarios. Each one has the expected impact, how to cause it in the Learner Lab, what to measure against the targets (**RPO 5 minutes**, **RTO 1 hour**) and the fix.

Run them with the stack deployed in the Learner Lab (see [`load-test.md`](load-test.md)). Keep the load test's autosave phase running during tests 1 and 2, so there is real traffic to lose:

```bash
python3 scripts/load_test.py run --label failure-bg --duration 900 &   # 15 min of autosave traffic
```

Record the measured values in each "Result" row and save the output and screenshots in `evidence/`.

---

## Test 1: Loss of an Availability Zone (database failover)

| | |
| --- | --- |
| **Scenario** | AZ A fails while students are autosaving. In the lab this is simulated by forcing the RDS primary to fail over to the standby in AZ B (an AZ cannot be switched off in AWS). |
| **Expected impact** | DynamoDB, S3, SQS and Lambda are unaffected because they are multi-AZ. RDS is unavailable for about 60–120 s while the standby is promoted: exam starts and result pages return 503 and retry. **Autosave keeps working** because it uses DynamoDB. |
| **How to run** | `scripts/simulate-az-failover.sh` (runs `aws rds reboot-db-instance --force-failover` and polls `/api/health?deep=1` every 2 s) |
| **Measure** | **RTO:** seconds from the first 503 to the first 200 on the deep health check (the script logs both). **RPO:** autosave errors in the background run (`evidence/load-test-failure-bg.json`) and the RDS `Multi-AZ` event log showing a synchronous standby, which means no committed transactions are lost. |
| **Pass if** | Database back in under 5 minutes, which is far under the 1-hour RTO; autosave error rate under 1%. |
| **Fix if it fails** | Use RDS Proxy (production profile): it holds client connections during failover and cuts reconnect time. Make the browser retry exam starts with backoff. |
| **Result (measured 19 Nov 2026, 3 runs)** | API outage **≤ 16 s, ≤ 14 s, ≤ 17 s** (last successful to first successful health check): one request timed out and 1–2 returned 503, then recovery was automatic. The primary moved us-east-1b → 1a → 1b → 1a. **RTO met** (17 s against 1 hour). **RPO met**: synchronous standby, so no committed data lost; autosave uses DynamoDB and was not affected. Full timeline: [`../evidence/az-failover.log`](../evidence/az-failover.log) |

## Test 2: Lambda throttling (compute limit reached)

| | |
| --- | --- |
| **Scenario** | The API function hits its concurrency limit. This happens if the account limit is too low, or if another function uses up the shared pool. It is simulated by limiting the function to 2 concurrent executions. |
| **Expected impact** | API Gateway returns 503 for requests over the limit. The browser marks saves "Offline – retrying", keeps answers in `localStorage` and resends them on the next 30-second autosave, so answers are delayed, not lost. The new `api-throttles` alarm fires. |
| **How to run** | `aws lambda put-function-concurrency --function-name uniexam-prod-api --reserved-concurrent-executions 2`, wait 3 minutes, then `aws lambda delete-function-concurrency --function-name uniexam-prod-api` |
| **Measure** | Error rate and p95 latency in the background run during the throttle window; the `Throttles` metric; time from removing the limit until errors stop (**RTO**), read from the 10-second timeline written by `scripts/failure_timeline.py`. **RPO:** the oldest unsaved answer is at most the throttle duration plus 30 s, and the copy in `localStorage` covers it. |
| **Pass if** | Recovery under 1 minute after the limit is removed; the alarm fired; no data lost once retries succeed. |
| **Fix** | A `Throttles` alarm (added in A3); request a higher account concurrency quota before exam week; reserve concurrency for `api` so background workers cannot starve it. |
| **Result** | Errors during throttle: ___ % · Alarm fired: yes/no · Recovery: ___ s |

## Test 3: Marking pipeline failure (bad message and worker down)

| | |
| --- | --- |
| **Scenario** | The marker cannot process submissions, because of a bug or because the database is unavailable to it. It is simulated in two steps: (a) stop the worker by setting its concurrency to 0 while students submit; (b) send a malformed message. |
| **Expected impact** | (a) Submissions wait in the `marking` queue; students are unaffected because submit returns immediately; results are delayed. (b) The bad message fails 5 times, moves to the dead-letter queue and raises the DLQ alarm; other messages carry on. This takes about 15 minutes, because each of the 5 receives waits for the 180-second visibility timeout. |
| **How to run** | (a) `aws lambda put-function-concurrency --function-name uniexam-prod-marker --reserved-concurrent-executions 0`, submit a few attempts from the app, wait 5 min, then `delete-function-concurrency`. (b) `aws sqs send-message --queue-url $(aws sqs get-queue-url --queue-name uniexam-prod-marking --query QueueUrl --output text) --message-body '{"bad":true}'` |
| **Measure** | `ApproximateNumberOfMessagesVisible` and `ApproximateAgeOfOldestMessage` on the queue; time from re-enabling the worker to the queue reaching 0 (**RTO for marking**); messages in the DLQ. **RPO:** count the results rows against the submissions, which should be equal (no submission lost). |
| **Pass if** | Every queued submission is marked after recovery; the bad message is in the DLQ and its alarm fired; marking resumes within minutes. |
| **Fix** | DLQ redrive after fixing the bug (`aws sqs start-message-move-task`); marking is idempotent, so redrive is safe. |
| **Result** | Backlog peak: ___ msgs · Drain time: ___ s · DLQ messages: ___ · Lost: ___ |

## Test 4: Accidental data deletion (point-in-time restore)

| | |
| --- | --- |
| **Scenario** | An operator or a bug deletes live attempts in DynamoDB (for example `delete-item` on the wrong key, or a bad script). |
| **Expected impact** | The affected students' saved answers vanish from the server. The browser still has its `localStorage` copy, but other devices do not. Nothing fails over automatically, so this tests the backup and restore path. |
| **How to run** | 1. Note the time T. 2. Delete one attempt: `aws dynamodb delete-item --table-name uniexam-prod-attempts --key '{"attempt_id":{"S":"<exam_id>#<student_sub>"}}'`. 3. Restore: `aws dynamodb restore-table-to-point-in-time --source-table-name uniexam-prod-attempts --target-table-name uniexam-prod-attempts-restored --restore-date-time <T>`. 4. Wait: `aws dynamodb wait table-exists --table-name uniexam-prod-attempts-restored`. 5. Copy the item back with `get-item` and `put-item`. |
| **Measure** | **RTO:** time from starting the restore to the table being ACTIVE, plus copying the item back. **RPO:** PITR restores to any second in the last 35 days, so data loss is only what was written between T and the deletion. |
| **Pass if** | Restore plus copy-back takes under 1 hour; the restored item has the answers saved before T. |
| **Fix** | Already designed: PITR on DynamoDB and RDS, plus AWS Backup. Also: deny `dynamodb:DeleteItem` and `DeleteTable` to humans in production through IAM, and turn on table deletion protection. |
| **Result** | Restore time: ___ min · Data recovered: yes/no · RPO achieved: ___ s |

Delete the restored table afterwards: `aws dynamodb delete-table --table-name uniexam-prod-attempts-restored`.

---

## Summary against the targets

| Test | Expected RTO | Expected RPO | Measured RTO | Measured RPO | Meets target? |
| --- | --- | --- | --- | --- | --- |
| 1 AZ / DB failover | 1–2 min | 0 (synchronous standby) | **≤ 17 s** | **0** | **Yes** |
| 2 Lambda throttling | < 1 min after the limit is removed | 0 (browser retries) | | | |
| 3 Marking failure | Minutes (queue drain) | 0 (durable queue + DLQ) | | | |
| 4 Accidental deletion | 10–30 min (PITR restore) | Seconds | | | |
