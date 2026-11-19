# AWS Pricing Calculator: inputs for both load profiles

The rubric needs both profiles entered in the official calculator, with exports in `evidence/`. Use the values below; they are the same inputs as [`../scripts/cost_model.py`](../scripts/cost_model.py), so the calculator total should land within a few percent of the cost report.

1. Open <https://calculator.aws/#/estimate> and click **Create estimate**.
2. Make **two estimates**: `UniExam – normal month` and `UniExam – exam month`. In each, add a group called `UniExam` and set the **Region to Asia Pacific (Singapore)** for every service.
3. For each estimate: **Save and share**, then copy the link into the README, then **Export → CSV** (and PDF) into `evidence/calculator-normal.csv`, `evidence/calculator-exam.csv` and so on.
4. Write down the date you checked the prices; it goes in the README.

| Service in calculator | Setting | Normal month | Exam month |
| --- | --- | --- | --- |
| **AWS Lambda** | Architecture arm64, requests, duration 120 ms, memory 512 MB | 8.79 M requests (api + workers) | 18.94 M |
| | Free tier | Exclude (untick) | Exclude |
| **Amazon API Gateway** | HTTP API, requests | 8.64 M | 18.64 M |
| **Amazon RDS for PostgreSQL** | db.t4g.medium, Multi-AZ, **Reserved 1 yr Partial Upfront**, 1 node | 730 h | 730 h |
| | Storage gp3 | 50 GB | 50 GB |
| | Backup storage (beyond free) | 0 GB | 0 GB |
| **RDS Proxy** | (inside the RDS PostgreSQL calculator) vCPU of instance | 2 vCPU, 730 h | same |
| **Amazon DynamoDB** | On-demand; write request units | 8 M | 46.4 M |
| | Read request units | 10 M | 25 M |
| | Data storage | 5 GB | 8 GB |
| | Point-in-time recovery | 5 GB | 8 GB |
| **Amazon VPC** | NAT gateways | 2, 730 h each | 2 |
| | Data processed per NAT gateway | 10 GB | 20 GB |
| | Public IPv4 addresses (in-use) | 2 | 2 |
| **Amazon S3** | S3 Standard | 320 GB, 32,000 PUT, 200,000 GET | same |
| | S3 Standard-IA | 560 GB | same |
| | S3 Glacier Instant Retrieval | 1,200 GB | same |
| | *(these three are the year-1 average spread across tiers)* | | |
| **Amazon CloudFront** | Data transfer out to internet, India | 550 GB (incl. 480 GB downloads) | 620 GB |
| | HTTPS requests, India | 9.64 M | 20.64 M |
| **AWS WAF** | 1 web ACL, 4 rules, requests | 9.64 M | 20.64 M |
| **Amazon CloudWatch** | Logs ingested (standard) | 6 GB | 13.2 GB |
| | Log storage | 3 GB | 6 GB |
| | Standard alarms / dashboards | 12 / 1 | 12 / 1 |
| **AWS X-Ray** | Traces recorded | 432,000 | 932,000 |
| **AWS KMS** | Customer managed keys / requests | 1 / 300,000 | 1 / 600,000 |
| **AWS Secrets Manager** | Secrets / API calls | 1 / 10,000 | 1 / 20,000 |
| **Amazon SQS** | Standard queue requests | 1.5 M | 3 M |
| **Amazon SES** | E-mails from EC2/Lambda | 64,000 | 104,000 |
| **AWS Backup** | RDS snapshot storage / DynamoDB backup | 40 GB / 30 GB | same |
| **Amazon Route 53** | 1 hosted zone, standard queries | 2 M | 4 M |
| **Data transfer** | Inter-AZ (EC2 → EC2 same Region) | 30 GB | 60 GB |
| **Amazon Cognito** | User pool Essentials, MAU | 8,400 | 8,400 |

For the **optimisation evidence**, duplicate the normal-month estimate as `UniExam – baseline (Assignment 2)` with these changes: RDS **On-Demand** instead of Reserved; S3 → **remove** the CloudFront downloads and add **480 GB data transfer out from S3 to the internet**; CloudWatch Logs **15 GB** ingested with **15 GB** stored. The difference between the two estimates is the saving per month.
