# Price sources

All prices are AWS public on-demand list prices in USD, **checked on 19 November 2026**. They were read from the AWS Price List API, which publishes the same data the AWS Pricing Calculator uses:

`https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/<ServiceCode>/current/<region>/index.json`

| Service code | Singapore file published | Key prices used (ap-southeast-1) |
| --- | --- | --- |
| AWSLambda | 2026-11-18 | USD 0.0000133334 per GB-s (arm64), USD 0.20 per million requests |
| AmazonApiGateway (calculator price map) | 2026-11-12 | HTTP API USD 1.25 per million (first 300 M) |
| AmazonRDS | 2026-11-17 | PostgreSQL db.t4g.medium Multi-AZ USD 0.203/h; 1-yr RI partial upfront USD 668 + USD 0.0762/h; db.m7g.large Multi-AZ USD 0.468/h; gp3 Multi-AZ USD 0.276/GB-mo; RDS Proxy USD 0.018/vCPU-h; Aurora Serverless v2 USD 0.20/ACU-h |
| AmazonDynamoDB | 2026-11-11 | On-demand USD 0.71 per million WRU, USD 0.1425 per million RRU; PITR USD 0.228/GB-mo |
| AmazonEC2 (NAT gateway) | 2026-11-18 | USD 0.059 per NAT gateway hour, USD 0.059 per GB processed |
| AmazonVPC | 2026-11-17 | Interface endpoint USD 0.013/h, USD 0.01/GB; public IPv4 USD 0.005/h |
| AmazonS3 | 2026-11-18 | Standard USD 0.025, Standard-IA USD 0.0138, Glacier IR USD 0.005 per GB-mo; PUT USD 0.005 per 1,000 |
| AWSDataTransfer | 2026-11-17 | Out to internet USD 0.12/GB (first 10 TB, after the 100 GB global free tier) |
| AmazonCloudFront (calculator price map) | 2026-11 | India edge HTTPS requests USD 0.012 per 10,000; always-free 1 TB and 10 M requests per month |
| awswaf | 2026-09-14 | Web ACL USD 5/month, rule USD 1/month, USD 0.60 per million requests |
| AmazonCloudWatch | 2026-11-16 | Logs ingestion USD 0.70/GB, storage USD 0.03/GB-mo, alarm USD 0.10, dashboard USD 3 |
| awskms | 2026-11-08 | USD 1 per key, USD 0.03 per 10,000 requests |
| AWSSecretsManager | 2026-11-11 | USD 0.40 per secret |
| AWSQueueService | 2026-11-11 | USD 0.40 per million standard requests (first 1 M free) |
| AWSXRay | 2026-11-08 | USD 5 per million traces stored |
| AmazonSES | 2026-11-04 | USD 0.10 per 1,000 e-mails |

Mumbai (ap-south-1) prices for the Region comparison come from the same files for `ap-south-1`. They are listed in [`../scripts/cost_model.py`](../scripts/cost_model.py). The Mumbai 1-year RI price is scaled from Singapore's discount; confirm it in the calculator.
