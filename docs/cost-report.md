# Cost and service report: UniExam in Singapore (ap-southeast-1)

**Verdict: feasible.** The optimised design costs an estimated **USD 4,239 a year, an average of USD 353 a month**. That is 35% of the USD 1,000 monthly budget, or **USD 0.53 per student per year**. It meets the peak load, the RPO and the RTO; the load test and failure tests in [`../infra/`](../infra) are how this is checked.

- Prices are AWS public on-demand prices for **Asia Pacific (Singapore)**, read from the AWS Price List API on **19 November 2026** (publication dates 4–18 November 2026). Sources are listed in [`../evidence/price-sources.md`](../evidence/price-sources.md).
- Every figure below is produced by [`../scripts/cost_model.py`](../scripts/cost_model.py). The AWS Pricing Calculator estimates for both load profiles are in [`../evidence/`](../evidence), and the links are in the [README](../README.md).

## 1. Workload assumptions

| Item | Normal month (×10) | Exam month (×2) | Basis |
| --- | --- | --- | --- |
| Concurrent users | 300–500 (400 average) | 3,000 at peak | Brief |
| API requests | 8.64 M | 18.64 M | 400 users × 12 h/day × 1 call/min; plus 40,000 exam attempts × 250 calls |
| Exam attempts | — | 40,000 | 8,000 students × 5 exams, 2 h each |
| Autosave writes | ~2 M | 9.6 M extra | Every 30 s, 240 per attempt; a 4 KB answer item costs 4 write units |
| Lambda | 512 MB arm64, 120 ms average | same | Deliberately cautious: the load test measured 12 ms (warm p95) for exam requests. Staff pages and reports run longer queries, so the model keeps 120 ms |
| New uploads | 320 GB | 320 GB | 8,000 students × 4 assignments × 10 MB |
| Downloads by tutors | 480 GB | 480 GB | Each file opened about 1.5 times |
| Log ingestion | 15 GB | 33 GB | About 1 KB of Lambda log plus 0.5 KB of API access log per request |
| E-mails | 64,000 | 104,000 | Submission notices, receipts and results |
| Users (MAU) | 8,400 | 8,400 | Inside the Cognito Essentials free tier of 10,000 MAU |

Peak arithmetic: 3,000 starts in 5 minutes is **10 starts per second**; 3,000 students saving every 30 s is **100 writes per second**.

## 2. Monthly cost per service

Optimised design in Singapore. Rows marked *hidden* are the costs the brief asks for that do not appear as a "service" on most diagrams.

| Service | Normal month (USD) | Exam month (USD) | Hidden? | Notes |
| --- | ---: | ---: | --- | --- |
| RDS PostgreSQL Multi-AZ, db.t4g.medium | 111.29 | 111.29 | | 1-year Reserved Instance, partial upfront (USD 668 + USD 0.0762/h) |
| NAT gateways ×2 + public IPv4 | 94.62 | 95.80 | **yes** | USD 0.059/h each, USD 0.059/GB processed, USD 0.005/h per IPv4 |
| DynamoDB on-demand | 8.24 | 38.33 | | USD 0.71 per million write units; PITR USD 0.228/GB |
| S3 uploads, lifecycle (year-1 average) | 21.89 | 21.89 | | Standard → IA 30 d → Glacier IR 90 d → Deep Archive 365 d |
| RDS Proxy | 26.28 | 26.28 | | USD 0.018 per vCPU-hour × 2 vCPU |
| API Gateway HTTP API | 10.80 | 23.30 | | USD 1.25 per million requests |
| AWS WAF | 14.78 | 21.38 | | 1 web ACL, 4 rules, USD 0.60 per million requests |
| AWS Lambda | 8.82 | 19.00 | | USD 0.0000133334 per GB-second (arm64) |
| RDS storage, 50 GB gp3 Multi-AZ | 13.80 | 13.80 | | USD 0.276 per GB-month |
| CloudFront | 0.00 | 12.77 | | Always-free 1 TB and 10 M requests; USD 0.012 per 10,000 HTTPS requests above that |
| SES | 6.40 | 10.40 | | USD 0.10 per 1,000 e-mails |
| CloudWatch Logs | 4.28 | 9.42 | **yes** | USD 0.70/GB ingested; 14-day retention |
| AWS Backup | 7.22 | 7.22 | **yes** | Monthly copies kept 5 years |
| CloudWatch alarms and dashboard | 4.20 | 4.20 | | 12 alarms and 1 dashboard |
| KMS | 1.84 | 2.74 | **yes** | USD 1 per key + USD 0.03 per 10,000 requests |
| Route 53 | 1.30 | 2.10 | | |
| Inter-AZ traffic | 0.60 | 1.20 | **yes** | Lambda in one AZ talking to RDS in the other |
| SQS | 0.20 | 0.80 | | First 1 M requests free |
| X-Ray | 1.66 | 4.16 | | Default Lambda sampling (1 req/s + 5%) |
| Secrets Manager | 0.40 | 0.40 | | |
| Data transfer out (downloads) | 0.00 | 0.00 | **yes** | Moved behind CloudFront; was USD 45.60/month (see §6) |
| Cognito | 0.00 | 0.00 | | Under 10,000 MAU |
| **Total** | **338.63** | **426.49** | | |

**Annual total:** 10 × 338.63 + 2 × 426.49 = **USD 4,239.31** (average USD 353.28 per month).
**Cost per student:** 4,239.31 ÷ 8,000 = **USD 0.53 per year**, about USD 0.04 per month.

The un-optimised Assignment 2 design would cost USD 5,392.86 a year (USD 449.40 per month), so the four optimisations in §6 save USD 1,154 a year (21%).

## 3. The three most expensive components

1. **RDS PostgreSQL Multi-AZ (USD 111/month, 33% of a normal month).** It is the only always-on server. Multi-AZ doubles the instance price, because AWS bills for a synchronous standby that does nothing until a failover. This is the price of surviving an AZ loss with zero data loss, so it is accepted.
2. **NAT gateways (USD 95/month, 28%).** Two gateways run 24 hours a day so each AZ has its own outbound path. Very little traffic goes through them, because DynamoDB and S3 use free gateway endpoints, so almost all of the cost is the hourly charge plus the public IPv4 charge introduced in 2024. Section 4.3 shows that replacing them with interface endpoints saves nothing.
3. **S3 storage (USD 22/month, year-1 average).** This grows by 320 GB a month and is the only cost that keeps rising. Without lifecycle rules, year 1 would average USD 52/month in S3 Standard and year 5 would reach about USD 480/month. With the rules, data older than a year falls to USD 0.002/GB in Deep Archive.

In an exam month, **DynamoDB** rises to fourth place (USD 38) because of the 9.6 million autosaves. It is the cheapest way to absorb them; §4.2 compares it with RDS.

## 4. Service choices compared with an alternative

### 4.1 Backend compute: Lambda vs ECS Fargate vs EC2 Auto Scaling

| | **Lambda (chosen)** | ECS Fargate | EC2 Auto Scaling |
| --- | --- | --- | --- |
| Cost, normal month | USD 8.82 | ~USD 72: 2 tasks × 0.5 vCPU / 1 GB, always on in 2 AZs | ~USD 60: 2 × t4g.small plus an ALB at about USD 25 |
| Cost, exam month | USD 19.00 | ~USD 150 with scale-out | ~USD 120 with scale-out |
| Performance at the peak | Scales per request in seconds; 10 starts/s needs ~2–15 concurrent executions | Scaling takes 1–3 min per task: too slow for a 5-minute spike unless pre-scaled | Instances take 3–5 min to boot; must be pre-warmed before exams |
| Resilience | Runs in both AZs by default | Tasks spread across AZs | Instances spread across AZs |
| Effort | No servers to patch | Images and task definitions | AMIs, patching, scaling policies |

Lambda is about 8× cheaper here because the platform is idle most of the time, and it is the only option that scales fast enough for a 5-minute surge without paying for pre-warmed capacity.

### 4.2 Storing answers: DynamoDB vs RDS Multi-AZ vs Aurora Serverless v2

| | **DynamoDB on-demand (chosen)** | Write autosaves to RDS | Aurora Serverless v2 |
| --- | --- | --- | --- |
| Extra cost, exam month | USD 38 | USD 0 at first, but needs db.m7g.large in exam months: +USD 194/month | Min 0.5 ACU × 2 instances × USD 0.20 = USD 146/month baseline, scaling to ~8 ACU at peak |
| Performance | Single-digit ms; no connection limit | 100 writes/s plus connections from every Lambda; CPU-bound on t4g | Good, but scaling up takes seconds and connections are still needed |
| Resilience | 3 AZs, PITR, RPO of seconds | Multi-AZ, failover 60–120 s during which saves fail | Multi-AZ with a reader; faster failover (~30 s) |
| Effort | No capacity planning | Bigger instance and tuning | New engine, migration |

### 4.3 Private traffic: NAT gateways vs VPC interface endpoints

| | **2 NAT gateways (chosen)** | Interface endpoints | 1 NAT gateway |
| --- | --- | --- | --- |
| Cost | USD 94.62 | 5 services (SQS, KMS, Secrets Manager, Cognito, X-Ray) × 2 AZ × USD 0.013 × 730 h = USD 94.90 | USD 47.31 |
| Performance | Same | Same, and slightly lower latency | Same |
| Resilience | Each AZ independent | Each AZ independent | **Single point of failure**: losing that AZ cuts outbound access in the other |
| Effort | One resource per AZ | 5 endpoints, a security group and DNS | One resource |

Interface endpoints cost the same and add more resources to manage, so NAT gateways stay. One NAT would save USD 47 a month but reintroduces the single point of failure the brief forbids, so it is rejected for production and only used in the test lab.

### 4.4 Paying for the database: On-Demand vs Reserved Instance vs Savings Plan

| db.t4g.medium Multi-AZ | **1-yr RI, partial upfront (chosen)** | On-Demand | 1-yr RI, no upfront |
| --- | --- | --- | --- |
| Annual cost | USD 668 + 0.0762 × 8,760 = USD 1,335 | 0.203 × 8,760 = USD 1,778 | 0.1605 × 8,760 = USD 1,406 |
| Saving | **USD 443 (25%)** | — | USD 372 (21%) |
| Risk | Locked to t4g.medium for a year | None | Same lock-in |

Compute Savings Plans do not cover RDS. Lambda's spend (about USD 130 a year) is too small for a Savings Plan to matter.

### 4.5 Five-year file retention: lifecycle rules vs Intelligent-Tiering vs Glacier only

| Year-1 average | **Lifecycle, GIR at 90 days (chosen)** | Lifecycle, GIR at 180 days (Assignment 2) | S3 Intelligent-Tiering | Straight to Deep Archive |
| --- | ---: | ---: | ---: | ---: |
| USD per month | **21.89** | 27.52 | 22.25 (incl. USD 0.52 monitoring) | ~6 |
| Years 2–5 | Deep Archive at USD 0.002/GB after 1 year | Same | Stays at USD 0.005/GB unless the asynchronous archive tiers are enabled | USD 0.002/GB |
| Retrieval | Milliseconds until 1 year, then 12–48 h | Same | Milliseconds | 12–48 h, even for this week's work |

Intelligent-Tiering beat the Assignment 2 rules. Retuning the rules to move files to Glacier Instant Retrieval at 90 days makes them slightly cheaper than Intelligent-Tiering in year 1, and much cheaper from year 2, because the rules also move files to Deep Archive. Deep Archive alone is cheapest but would stop tutors from opening recent submissions.

## 5. Singapore compared with Mumbai, and latency from Bhutan

| | Singapore (ap-southeast-1) | Mumbai (ap-south-1) |
| --- | --- | --- |
| Annual cost, optimised | USD 4,239 | USD 3,896 (8% less) |
| Main differences | RDS Multi-AZ USD 0.203/h; NAT USD 0.059/h; HTTP API USD 1.25 per million | RDS USD 0.167/h; NAT USD 0.056/h; HTTP API USD 1.05 per million |
| TCP connect from Bhutan, median | **84 ms** | **74 ms** |
| AZs | 3 | 3 |

Latency was measured from the author's laptop in Bhutan with 8 TCP connections to each Region's DynamoDB endpoint ([`../evidence/latency-from-bhutan.txt`](../evidence/latency-from-bhutan.txt)). Both are well inside what a web exam needs; an autosave every 30 s is not latency-sensitive. Static files come from the nearest CloudFront edge (in India) whichever Region is chosen.

Mumbai is cheaper and about 10 ms closer. Singapore is acceptable and is what the university asked for. The recommendation is to stay in Singapore unless the university has no reason to prefer it, in which case Mumbai saves about USD 343 a year.

## 6. Optimisations and their savings

| # | Optimisation | Saving per year | How |
| --- | --- | ---: | --- |
| 1 | Serve submission downloads through CloudFront instead of direct S3 presigned URLs | **USD 547** | Transfer from S3 to CloudFront is free, and 480 GB a month fits CloudFront's always-free 1 TB; direct S3 transfer costs USD 0.12/GB |
| 2 | 1-year Reserved Instance for the RDS Multi-AZ instance (partial upfront) | **USD 443** | See §4.4 |
| 3 | Leaner logging: 14-day retention (was 30), Lambda platform START/END/REPORT lines dropped (`system_log_level = WARN`), API access logs off in production | **USD 96** | Logs fall from about 15 GB to 6 GB a month |
| | 4 | Move files to Glacier Instant Retrieval at 90 days instead of 180 | **USD 68** | Files are rarely opened after the first month; GIR still returns them in milliseconds |
| | **Total** | **USD 1,154** | Baseline USD 5,393 → optimised USD 4,239 |

Not adopted:
- **Dropping RDS Proxy (USD 315 a year).** The load test needed only 13 database connections at the brief's peak, so the Proxy is not needed for capacity at this scale. It is kept because it shortens database failovers and protects against connection exhaustion if traffic grows.
- **Replacing NAT with interface endpoints.** It saves nothing (§4.3).

**Added after the load test: provisioned concurrency during exam windows.** The load test found the only slow requests were API Lambda cold starts, at 1.1–1.5 s each ([`../infra/load-test.md`](../infra/load-test.md)). The fix is 15 pre-warmed environments of 512 MB, switched on only for exam sittings: 14 sittings of 2 h, plus 30 minutes of warm-up each, is 35 h per exam month. At USD 0.0000041593 per GB-second (arm64, Singapore), this costs **USD 3.93 per exam month, or USD 7.86 a year**. It would raise the optimised annual total from USD 4,239 to USD 4,247, still 35% of the budget. The Learner Lab denies it, so it was not tested there. The model leaves it out of the headline totals, so the totals stay comparable with the Pricing Calculator estimates.

## 7. Feasibility verdict

| Question | Answer | Evidence |
| --- | --- | --- |
| Within USD 1,000 a month (yearly average)? | **Yes**: USD 353, leaving USD 647 of headroom | §2 |
| Still within budget if exam months need a bigger database? | **Yes**: moving to db.m7g.large Multi-AZ for the 2 exam months adds USD 387 a year (USD 386/month average) | 0.468 − 0.203 USD/h × 730 h × 2 |
| Handles the peak (10 starts/s, 100 saves/s)? | **Yes, measured**: 0 errors in about 30,300 requests per run, start p95 55–94 ms, autosave p95 42–43 ms. RDS CPU peaked at 6.4% with 13 connections. The only slow requests were 13 Lambda cold starts per run, at 1.1–1.5 s each | [`../infra/load-test.md`](../infra/load-test.md) |
| RPO of 5 minutes? | **Yes**: autosave every 30 s, synchronous Multi-AZ replication, PITR | [`../infra/failure-tests.md`](../infra/failure-tests.md) |
| RTO of 1 hour? | **Yes, measured**: three forced database failovers caused API outages of at most 17 s; a PITR restore or redeploy takes 20–40 minutes | Failure tests 1 and 4; [`../evidence/az-failover.log`](../evidence/az-failover.log) |
| Survives the loss of an AZ? | **Yes**: every tier is in two AZs | [`../architecture/README.md`](../architecture/README.md) |
| Keeps files for 5 years? | **Yes**: lifecycle expiry at 1,825 days; Backup keeps monthly copies for 5 years | §4.5 |

The expected cost risk was the database, because the brief's peak lands on a burstable t4g instance that can run out of CPU credits. The load test showed this risk is low: the API caches each exam paper, so even the lab's smaller db.t4g.micro peaked at 6.4% CPU, and its credit balance did not fall. The fallback (a larger instance in exam months) still fits the budget if real exams prove heavier than the test.
