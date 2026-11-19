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
python3 scripts/cloudwatch_summary.py run1-t4g-micro              # metrics + Logs Insights -> evidence/cloudwatch-run1-t4g-micro.md
#   -> screenshot the CloudWatch graphs below for the printed time window
#   -> apply the fix (section 3), wait for it to finish
python3 scripts/load_test.py run --label run2-after-fix         # re-test
python3 scripts/cloudwatch_summary.py run2-after-fix
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

### What CloudWatch actually showed (run 1)

The hypothesis was **wrong**, and CloudWatch shows why (`evidence/cloudwatch-run1-t4g-micro.md`):

- **The database is idle.** RDS CPU peaked at 6.4%, the CPU credit balance stayed at 72, and there were only 13 connections. The schema statements took 18 ms on average (37 ms at most) per new environment. The API caches each exam paper in memory, so the start storm hardly touches RDS.
- **The slow requests are Lambda cold starts.** 13 new environments started (Lambda peak concurrency was also 13), each with an average init time of 813 ms (1,089 ms at most). On its first request each one also opened a database connection, which took 309 ms on average (Secrets Manager call plus TLS handshake). A student who lands on a new environment therefore waits about 1.1–1.2 s, which matches the API Gateway p99 of 1,196 ms. Warm requests take 12 ms in Lambda (p95).
- 10 of the 13 cold starts happened in the first 90 seconds, during the start storm; the per-30-second Logs Insights table shows this.

**Bottleneck: cold starts of the API Lambda during the start storm**, about 1.1 s each, including about 0.3 s to connect to the database. It does not break the p95 target, but it is the only thing that makes any request slow, and it hits exactly the moment students press "Start".

**Fixes considered:**

| Fix | Change | Evidence for or against | Cost |
| --- | --- | --- | --- |
| A | Only run the schema statements when the schema is missing | Saves at most about 18 ms per cold start. **Not worth it.** | None |
| B | RDS Proxy | Lambda still opens a TLS connection to the proxy on its first request, so it shortens the 309 ms only partly and does nothing about the 813 ms init. Useful for connection counts at larger scale; not available in the lab. | USD 26/month (already in the design) |
| C | db.t4g.medium | The database CPU is at 6.4%, so a bigger instance would change nothing. **Rejected.** | +USD 74/month |
| D | **Provisioned concurrency of 15 on the API alias during exam windows**, sized from the measured peak of 13 plus headroom. Each pre-warmed environment also opens its database connection while it is being prepared (`backend/api.py`, only when `AWS_LAMBDA_INITIALIZATION_TYPE` is `provisioned-concurrency`). | Removes both the init time and the first connection time from the student's request. **Tried, but denied in the lab:** `lambda:PutProvisionedConcurrencyConfig` has an explicit deny in the Learner Lab service control policy. It remains the production recommendation for exam windows. | Only during exam windows; see the cost report |
| **E (applied)** | **More API Lambda memory: 512 MB to 1,769 MB** (`api_memory_mb`). Lambda allocates CPU in proportion to memory, and 1,769 MB is one full vCPU. | Init (loading libraries, creating clients) and the TLS handshake for the database connection are CPU work, so cold starts should shorten. Warm requests also get faster, which offsets the higher price per millisecond. | Measured in run 2; see the cost report |

Run 2 re-tests with fix E applied; the table below compares the two runs.

## 4. Results

The numbers come from `evidence/load-test-*.json` (measured by the client) and `evidence/cloudwatch-*.md` (measured by CloudWatch).

**First attempt rejected (test-tool bug).** The first run 1 reached only 4.6 starts per second, not 10. The script ran the start storm on a pool of 100 threads, so 300 students started in three waves instead of within 30 seconds. It also reused one exam, so a repeat run would only re-read existing attempts. The script now uses one thread per student and creates a new exam for every run. The rejected output is `load-test-run0-underdriven.json` (0 errors, start p95 98 ms, autosave 99 per second at p95 44 ms). It was lost when CloudShell restarted, so only these numbers remain. A second valid run 1 was made before the Lambda REPORT lines were switched on; it is kept as `evidence/load-test-run1a-before-logging.json` (start p95 53 ms, p99 436 ms, max 854 ms), and it agrees with run 1.

| Metric | Run 1 (512 MB) | Run 2 (fix E, 1,769 MB) | Target |
| --- | --- | --- | --- |
| Start storm rate | 10.0 /s | | 10 /s |
| Start storm p95 latency (client) | 94 ms | | < 1,000 ms |
| Start storm p99 / max (client) | 174 / 779 ms | | |
| Start storm error rate | 0% | | < 1% |
| API Gateway p99 latency (worst minute) | 1,196 ms | | < 1,000 ms |
| Lambda cold starts / average init | 13 / 813 ms | | |
| First DB connection (average) | 309 ms | | |
| Autosave rate achieved | 99.0 /s | | ≥ 100 /s (300 × 1 per 3 s) |
| Autosave p95 latency | 43 ms | | < 500 ms |
| Autosave error rate | 0% | | < 0.1% |
| RDS CPU max | 6.4% | | < 70% |
| RDS connections max | 13 | | < 80% of max_connections |
| Lambda throttles | 0 | | 0 |

**Finding:** CloudWatch disproved the database hypothesis (RDS CPU 6.4%, 13 connections, schema statements 18 ms). The slowest requests are API Lambda cold starts during the start storm: 813 ms init plus a 309 ms first database connection, which pushes the API Gateway p99 to 1.2 s.
**Fix applied:** E, API Lambda memory raised from 512 MB to 1,769 MB. Fix D (provisioned concurrency) was tried first, but the lab denies it.
**Re-test result:** *(after run 2)*

## 5. Two more bottlenecks, reasoned (not tested)

1. **Cognito sign-in rate.** Cognito user pools have a default quota for user authentication API calls per second (the `UserAuthentication` category, which includes `InitiateAuth`), shared by the whole account. 3,000 sign-ins in 5 minutes is about 10 per second, within the quota. But if every student signs in during the same minute before the exam, the rate becomes about 50 per second, close to the quota. **Mitigation:** open the sign-in page 30 minutes before the exam, rely on 60-minute tokens with silent refresh, and request a quota increase before exam week.
2. **End-of-exam marking surge.** 3,000 submissions arrive within about a minute. Marking concurrency is capped at 20 to protect the database, so the queue drains in roughly 3,000 × 0.3 s ÷ 20 ≈ 45 seconds. Results are only delayed, never lost; the `ApproximateAgeOfOldestMessage` alarm fires if the delay exceeds 10 minutes. **Mitigation:** raise the cap to 50 if the database has headroom, which the load test shows.
3. *(Optional third)* **DynamoDB item size.** Each autosave rewrites the whole answer item. A 30-question exam with long short answers can reach 10–20 KB, which is 10–20 write units per save. At 100 saves per second that is up to 2,000 write units per second and would multiply the DynamoDB line in the cost report by about 4. On-demand still absorbs it, but storing short answers as separate items would keep each save at 1–2 write units.
