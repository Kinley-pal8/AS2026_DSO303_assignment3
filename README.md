# UniExam: cost, feasibility and resilience analysis

DSO303 Assignment 3. This assignment analyses the Assignment 2 online exam platform (8,000 students, 400 staff) running in **Asia Pacific (Singapore), ap-southeast-1**: what it costs, whether it fits the USD 1,000-a-month budget, and where it fails or slows down.

## Summary

| | |
| --- | --- |
| **Annual cost (optimised)** | **USD 4,239**: USD 339 in a normal month, USD 426 in an exam month |
| **Average per month** | **USD 353**, which is 35% of the USD 1,000 budget |
| **Cost per student** | **USD 0.53 a year** |
| **Top 3 costs** | RDS Multi-AZ (33%), NAT gateways (28%), S3 storage |
| **Savings from optimisation** | USD 1,154 a year (21%) from four changes: CloudFront for downloads, an RDS Reserved Instance, leaner logging, Glacier IR at 90 days |
| **Region** | Singapore is 84 ms from Bhutan; Mumbai would be 74 ms and 8% cheaper |

## Feasibility verdict

**Feasible.** The design meets the budget with USD 647 a month of headroom. It stays within budget even if exam months need a larger database (+USD 387 a year). The load test measured the peak (10 starts/s, 100 autosaves/s) with 0 errors and a p95 under 100 ms. The database stayed at 6.4% CPU; the only slow requests were Lambda cold starts (1.1–1.5 s), fixed in production with provisioned concurrency during exam windows (+USD 8 a year). It meets the RPO of 5 minutes (30-second autosave, synchronous Multi-AZ standby, PITR) and the RTO of 1 hour (automatic AZ failover in minutes; PITR restore in under an hour). It survives the loss of an AZ, and files are kept for 5 years through lifecycle rules and AWS Backup. Full reasoning is in [docs/cost-report.md §7](docs/cost-report.md#7-feasibility-verdict).

## AWS Pricing Calculator

Prices checked: **19 November 2026**.

| Estimate | Link |
| --- | --- |
| Normal month (Singapore) | *add the calculator share link* |
| Exam month (Singapore) | *add the calculator share link* |
| Baseline, Assignment 2 design (for the savings) | *add the calculator share link* |

The exports are in [`evidence/`](evidence). The inputs are in [docs/pricing-calculator-guide.md](docs/pricing-calculator-guide.md).

## Demo video

*Add the link: at most 5 minutes, in your own voice, showing one failure test and the load test.*

## Repository layout

```
README.md                       this summary
architecture/README.md          revised diagram, single points of failure, change log vs Assignment 2
architecture/diagram.mmd        diagram source (Mermaid)
docs/cost-report.md             Task 2: cost per service, hidden costs, top 3, 5 comparisons, Region comparison, verdict
docs/pricing-calculator-guide.md  exact inputs for both load profiles in the AWS Pricing Calculator
infra/failure-tests.md          4 failure scenarios: expected impact, how to run, RPO/RTO measurement, fix
infra/load-test.md              load-test plan, CloudWatch evidence, bottleneck, fix and re-test
infra/*.tf                      Terraform for the whole platform (Singapore by default)
scripts/cost_model.py           reproduces every number in the cost report
scripts/load_test.py            exam-peak load generator (start storm + autosave)
scripts/simulate-az-failover.sh failure test 1
evidence/                       calculator exports, price sources, latency, load-test and failure-test results
backend/, frontend/             application code (from Assignment 2)
```

## How to reproduce

```bash
python3 scripts/cost_model.py              # the cost report figures
```

To run the load and failure tests, deploy to AWS Academy Learner Lab (us-east-1; the lab does not allow Singapore):

```bash
export AWS_PROFILE=lab AWS_REGION=us-east-1
./scripts/build.sh
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
# Same state as the Assignment 2 deployment: this upgrades that stack in place
# (the two use the same resource names, so they cannot run side by side).
cd infra
terraform init -backend-config="bucket=uniexam-tfstate-$ACCOUNT" -backend-config="key=uniexam/prod.tfstate" \
               -backend-config="region=us-east-1" -backend-config="use_lockfile=true"
terraform apply -var-file=learner-lab.tfvars -var="initial_admin_email=YOUR_EMAIL"
```

Then follow [infra/load-test.md](infra/load-test.md) and [infra/failure-tests.md](infra/failure-tests.md).

## Tear down

```bash
cd infra && terraform destroy -var-file=learner-lab.tfvars
```
