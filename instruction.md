# DSO303 Assignment 3– Cost, Feasibility and Resilience Analysis

## Scenario

The university now wants to know what your Assignment 2 exam platform will cost to run in **Asia Pacific (Singapore), ap-southeast-1**, whether it is affordable, and where it will fail or slow down.

- **Load profiles:** 10 normal months (300–500 concurrent users) and 2 exam months (peak of 3,000 students starting one exam within 5 minutes).
- **Budget:** USD 1,000 per month, averaged over the year.
- **Targets (unchanged):** RPO 5 minutes, RTO 1 hour, survives the loss of one AZ, files kept for 5 years.
- **Prices:** from the AWS Pricing Calculator, in USD, with the date checked.

## Tasks

**Task 1 – Revised architecture design.** Draw your final, cost-optimized architecture. Mark every single point of failure and how it is removed or accepted. Add a change log against Assignment 2.

**Task 2 – Cost and service report.** Cover:

1. Monthly cost per service for a normal month and an exam month, the annual total and the cost per student. Include hidden costs: data transfer out, NAT gateway processing, CloudWatch Logs, KMS requests and backups.
2. The three most expensive components and why.
3. At least four service choices compared with an alternative (cost, performance, resilience, effort), for example:
   - EC2 Auto Scaling, ECS Fargate or Lambda for the backend
   - RDS Multi-AZ, Aurora Serverless v2 or DynamoDB for answers
   - NAT gateway or VPC endpoints for private traffic
   - On-Demand, Savings Plans or Reserved Instances
   - S3 Standard, Intelligent-Tiering or Glacier for 5-year retention
4. Singapore compared with one other Region, including latency for users in Bhutan.
5. A feasibility verdict: does it meet the budget, peak load, RPO and RTO?

**Task 3 – Implementation.**

- **Costed estimate:** Both load profiles in the AWS Pricing Calculator, then at least three optimizations with the saving of each.
- **Failure tests:** At least three scenarios, each with expected impact on the infrastructure

## Deliverables

Submit in your own repository:

- `README.md` – summary, feasibility verdict, calculator links, and a demo video link (at most 5 minutes, in your own voice, showing one failure test and the load test)
- `architecture/` – revised diagram and change log if any
- `docs/cost-report.md` – cost and service report
- `infra/` – failure test scenarios, with the expected impact and a likely solution
- `evidence/` – calculator exports

## Marking rubric

| Criterion | Marks | Full marks | Partial | Low |
| --- | --- | --- | --- | --- |
| AWS architecture design | 2 | Design reflects cost and test findings; failure points marked; clear change log | Weak link to findings or change log (1–1.5) | Assignment 2 diagram resubmitted (0–0.5) |
| AWS service documentation | 2 | Full cost breakdown with hidden costs; four strong comparisons; Region comparison; verdict backed by numbers | Incomplete breakdown or unsupported verdict (1–1.5) | Unsourced costs, no verdict (0–0.5) |
| Implementation – costed estimate | 2 | Both profiles in the calculator; three optimisations with savings | One profile or fewer optimisations (1) | No calculator evidence (0) |
| Implementation – failure tests | 2 | Four scenarios measured against RPO and RTO, with fixes | Fewer scenarios or no measurements (1) | No tests (0) |
| Implementation – load test | 2 | Bottleneck proven with CloudWatch, fixed and re-tested; two more reasoned | Bottleneck asserted, not proven or re-tested (1) | No load test (0) |
| **Total** | **10** | | | |

_The tutor may ask you to explain or re-run your work in a short viva._