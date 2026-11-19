# Load test: exam peak

**Goal:** prove where the platform slows down at the exam peak, using CloudWatch, then fix it and re-test.

**Target load:** 3,000 students starting one exam within 5 minutes means **10 starts per second**. Then **100 autosaves per second** (3,000 students × one save every 30 s).

**How it is generated:** [`../scripts/load_test.py`](../scripts/load_test.py) signs in 300 test students and runs two phases:

1. **Start storm:** all 300 students start the exam within 30 seconds, giving 10 starts per second.
2. **Autosave:** each student saves every 3 seconds for 5 minutes, giving 100 writes per second.

The rates match the brief while needing only 300 accounts. The real path is exercised end to end: API Gateway with the JWT authorizer, then Lambda, then RDS (exam paper) and DynamoDB (attempt and answers). In production CloudFront sits in front; it is left out of the test because the Learner Lab denies CloudFront, and it only caches static files, which are not the bottleneck.

**Where:** AWS Academy Learner Lab, us-east-1, Learner Lab profile (no RDS Proxy, no CloudFront, one NAT). Pricing uses Singapore; Learner Lab only allows us-east-1 and us-west-2, and the behaviour under load does not depend on the Region.

## 1. Procedure

```bash
export AWS_PROFILE=lab AWS_REGION=us-east-1
cd ~/Desktop/DSO303_as3 && ./scripts/build.sh
cd infra && terraform apply -var-file=learner-lab.tfvars -var="initial_admin_email=YOUR_EMAIL" && cd ..

python3 scripts/load_test.py setup --students 300
python3 scripts/load_test.py run --label run1-t4g-micro       # before the fix
#   -> screenshot the CloudWatch graphs below for the printed time window
#   -> apply the fix (section 3), wait for it to finish
python3 scripts/load_test.py run --label run2-after-fix         # re-test
python3 scripts/load_test.py cleanup
```

The results are saved to `evidence/load-test-<label>.json`.

## 2. CloudWatch evidence to capture (both runs, same time window)

| Graph | Namespace / metric | What it proves |
| --- | --- | --- |
| API latency and errors | `AWS/ApiGateway` `Latency` (p95), `5xx`, `4xx` | What students experience |
| Lambda duration and throttles | `AWS/Lambda` `Duration` (p95), `ConcurrentExecutions`, `Throttles`, `Errors` for `uniexam-prod-api` | Whether compute is the limit |
| Database | `AWS/RDS` `CPUUtilization`, `CPUCreditBalance`, `DatabaseConnections`, `ReadLatency` | Whether the database is the limit |
| DynamoDB | `AWS/DynamoDB` `ConsumedWriteCapacityUnits`, `SuccessfulRequestLatency` (PutItem/UpdateItem), `ThrottledRequests` | Whether autosave storage is the limit |
| Cold starts | CloudWatch Logs Insights on `/aws/lambda/uniexam-prod-api`: `filter @type = "REPORT" | stats count(@initDuration), max(@initDuration), pct(@duration, 95) by bin(30s)` | Whether new Lambda environments slow the start storm |

Save each screenshot as `evidence/cw-<run>-<graph>.png`.

## 3. Expected bottleneck and fix

**Hypothesis: the database during the start storm.** Each new Lambda environment opens its own PostgreSQL connection and, on its first request, runs the schema check under an advisory lock (`backend/db.py`). The Learner Lab profile has no RDS Proxy, and the database is a db.t4g.micro (2 vCPU burstable, about 1 GB RAM). With up to about 50 new environments starting together, cold starts queue on the lock and the instance's CPU spikes.

**Signs in CloudWatch:**
- API p95 latency of several seconds during phase 1 only.
- High `@initDuration` together with long first-request durations.
- RDS `CPUUtilization` near 100% and `DatabaseConnections` rising with `ConcurrentExecutions`.
- Phase 2 (DynamoDB) stays fast.

**Fixes, in order of preference:**

| Fix | Change | Cost |
| --- | --- | --- |
| A | Only run the schema statements when the schema is missing (one `to_regclass` query instead of 6 DDL statements under a lock) | None |
| B | Use RDS Proxy (production profile) so connections are pooled | USD 26/month (already in the design) |
| C | Scale the database to db.t4g.medium (`-var="db_instance_class=db.t4g.medium"`) | +USD 74/month on demand |

Run 2 re-tests with the fix applied; the table below compares the two runs.

## 4. Results

*Filled in after running. The numbers come from `evidence/load-test-*.json` and the CloudWatch screenshots.*

**First attempt rejected (test-tool bug).** The first run 1 reached only 4.6 starts per second, not 10. The script ran the start storm on a pool of 100 threads, so 300 students started in three waves instead of within 30 seconds. It also reused one exam, so a repeat run would only re-read existing attempts. The script now uses one thread per student and creates a new exam for every run. The rejected output is kept as `evidence/load-test-run0-underdriven.json` (0 errors, start p95 98 ms, autosave 99 per second at p95 44 ms).

| Metric | Run 1 (before) | Run 2 (after fix) | Target |
| --- | --- | --- | --- |
| Start storm p95 latency | | | < 1,000 ms |
| Start storm error rate | | | < 1% |
| Autosave rate achieved | | | ≥ 100 /s |
| Autosave p95 latency | | | < 500 ms |
| Autosave error rate | | | < 0.1% |
| RDS CPU max | | | < 70% |
| RDS connections max | | | < 80% of max_connections |
| Lambda throttles | | | 0 |

**Finding:** *(one or two sentences after run 1: what CloudWatch proved)*
**Fix applied:** *(A, B or C)*
**Re-test result:** *(did run 2 meet the targets?)*

## 5. Two more bottlenecks, reasoned (not tested)

1. **Cognito sign-in rate.** Cognito user pools have a default quota for user authentication API calls per second (the `UserAuthentication` category, which includes `InitiateAuth`), shared by the whole account. 3,000 sign-ins in 5 minutes is about 10 per second, within the quota. But if every student signs in during the same minute before the exam, the rate becomes about 50 per second, close to the quota. **Mitigation:** open the sign-in page 30 minutes before the exam, rely on 60-minute tokens with silent refresh, and request a quota increase before exam week.
2. **End-of-exam marking surge.** 3,000 submissions arrive within about a minute. Marking concurrency is capped at 20 to protect the database, so the queue drains in roughly 3,000 × 0.3 s ÷ 20 ≈ 45 seconds. Results are only delayed, never lost; the `ApproximateAgeOfOldestMessage` alarm fires if the delay exceeds 10 minutes. **Mitigation:** raise the cap to 50 if the database has headroom, which the load test shows.
3. *(Optional third)* **DynamoDB item size.** Each autosave rewrites the whole answer item. A 30-question exam with long short answers can reach 10–20 KB, which is 10–20 write units per save. At 100 saves per second that is up to 2,000 write units per second and would multiply the DynamoDB line in the cost report by about 4. On-demand still absorbs it, but storing short answers as separate items would keep each save at 1–2 write units.
