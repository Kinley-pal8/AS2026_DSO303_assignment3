Workload: normal 8.64 M API requests, exam 18.64 M

## ap-southeast-1 - baseline (Assignment 2 design)

| Service | Normal month (USD) | Exam month (USD) | Hidden cost? |
| --- | ---: | ---: | --- |
| RDS PostgreSQL Multi-AZ (db.t4g.medium) | 148.19 | 148.19 |  |
| NAT gateways (2) + public IPv4 | 94.62 | 95.80 | yes |
| Data transfer out (S3 downloads) | 45.60 | 45.60 | yes |
| DynamoDB on-demand | 8.24 | 38.33 |  |
| S3 uploads (lifecycle, year-1 avg) | 27.52 | 27.52 |  |
| RDS Proxy (2 vCPU) | 26.28 | 26.28 |  |
| CloudWatch Logs | 10.95 | 24.09 | yes |
| API Gateway (HTTP API) | 10.80 | 23.30 |  |
| AWS WAF | 14.78 | 21.38 |  |
| AWS Lambda | 8.82 | 19.00 |  |
| RDS storage 50 GB gp3 Multi-AZ | 13.80 | 13.80 |  |
| CloudFront | 0.00 | 12.77 |  |
| SES | 6.40 | 10.40 |  |
| AWS Backup (RDS + DynamoDB) | 7.22 | 7.22 | yes |
| CloudWatch alarms + dashboard | 4.20 | 4.20 |  |
| X-Ray | 1.66 | 4.16 |  |
| KMS (1 CMK + requests) | 1.84 | 2.74 | yes |
| Route 53 | 1.30 | 2.10 |  |
| Inter-AZ data transfer | 0.60 | 1.20 | yes |
| SQS | 0.20 | 0.80 |  |
| Secrets Manager | 0.40 | 0.40 |  |
| Cognito (8,400 MAU, Essentials free tier) | 0.00 | 0.00 |  |
| **Total** | **433.43** | **529.28** | |

Annual (10 normal + 2 exam): 5,392.86 USD | average 449.40 USD/month | 0.67 USD per student per year

## ap-southeast-1 - optimised

| Service | Normal month (USD) | Exam month (USD) | Hidden cost? |
| --- | ---: | ---: | --- |
| RDS PostgreSQL Multi-AZ (db.t4g.medium) | 111.29 | 111.29 |  |
| NAT gateways (2) + public IPv4 | 94.62 | 95.80 | yes |
| DynamoDB on-demand | 8.24 | 38.33 |  |
| RDS Proxy (2 vCPU) | 26.28 | 26.28 |  |
| API Gateway (HTTP API) | 10.80 | 23.30 |  |
| S3 uploads (lifecycle, year-1 avg) | 21.89 | 21.89 |  |
| AWS WAF | 14.78 | 21.38 |  |
| AWS Lambda | 8.82 | 19.00 |  |
| RDS storage 50 GB gp3 Multi-AZ | 13.80 | 13.80 |  |
| CloudFront | 0.00 | 12.77 |  |
| SES | 6.40 | 10.40 |  |
| CloudWatch Logs | 4.28 | 9.42 | yes |
| AWS Backup (RDS + DynamoDB) | 7.22 | 7.22 | yes |
| CloudWatch alarms + dashboard | 4.20 | 4.20 |  |
| X-Ray | 1.66 | 4.16 |  |
| KMS (1 CMK + requests) | 1.84 | 2.74 | yes |
| Route 53 | 1.30 | 2.10 |  |
| Inter-AZ data transfer | 0.60 | 1.20 | yes |
| SQS | 0.20 | 0.80 |  |
| Secrets Manager | 0.40 | 0.40 |  |
| Data transfer out (S3 downloads) | 0.00 | 0.00 | yes |
| Cognito (8,400 MAU, Essentials free tier) | 0.00 | 0.00 |  |
| **Total** | **338.63** | **426.49** | |

Annual (10 normal + 2 exam): 4,239.31 USD | average 353.28 USD/month | 0.53 USD per student per year

Saving from all optimisations: 1,153.54 USD/year

  cf_downloads   saves   547.20 USD/year
  rds_ri         saves   442.77 USD/year
  lean_logs      saves    95.99 USD/year
  s3_gir90       saves    67.58 USD/year

Load-test recommendation, provisioned concurrency 15 x 512 MB for 35 h per exam month: 3.93 USD per exam month, 7.86 USD/year (optimised annual would be 4,247.17 USD)

## ap-south-1 - baseline (Assignment 2 design)

| Service | Normal month (USD) | Exam month (USD) | Hidden cost? |
| --- | ---: | ---: | --- |
| RDS PostgreSQL Multi-AZ (db.t4g.medium) | 121.91 | 121.91 |  |
| NAT gateways (2) + public IPv4 | 90.18 | 91.30 | yes |
| Data transfer out (S3 downloads) | 41.53 | 41.53 | yes |
| DynamoDB on-demand | 8.24 | 38.33 |  |
| S3 uploads (lifecycle, year-1 avg) | 27.52 | 27.52 |  |
| RDS Proxy (2 vCPU) | 24.82 | 24.82 |  |
| CloudWatch Logs | 10.50 | 23.10 | yes |
| AWS WAF | 14.78 | 21.38 |  |
| API Gateway (HTTP API) | 9.07 | 19.57 |  |
| AWS Lambda | 8.82 | 19.00 |  |
| RDS storage 50 GB gp3 Multi-AZ | 13.10 | 13.10 |  |
| CloudFront | 0.00 | 12.77 |  |
| SES | 6.40 | 10.40 |  |
| AWS Backup (RDS + DynamoDB) | 7.22 | 7.22 | yes |
| CloudWatch alarms + dashboard | 4.20 | 4.20 |  |
| X-Ray | 1.66 | 4.16 |  |
| KMS (1 CMK + requests) | 1.84 | 2.74 | yes |
| Route 53 | 1.30 | 2.10 |  |
| Inter-AZ data transfer | 0.60 | 1.20 | yes |
| SQS | 0.20 | 0.80 |  |
| Secrets Manager | 0.40 | 0.40 |  |
| Cognito (8,400 MAU, Essentials free tier) | 0.00 | 0.00 |  |
| **Total** | **394.31** | **487.56** | |

Annual (10 normal + 2 exam): 4,918.17 USD | average 409.85 USD/month | 0.61 USD per student per year

## ap-south-1 - optimised

| Service | Normal month (USD) | Exam month (USD) | Hidden cost? |
| --- | ---: | ---: | --- |
| RDS PostgreSQL Multi-AZ (db.t4g.medium) | 91.60 | 91.60 |  |
| NAT gateways (2) + public IPv4 | 90.18 | 91.30 | yes |
| DynamoDB on-demand | 8.24 | 38.33 |  |
| RDS Proxy (2 vCPU) | 24.82 | 24.82 |  |
| S3 uploads (lifecycle, year-1 avg) | 21.89 | 21.89 |  |
| AWS WAF | 14.78 | 21.38 |  |
| API Gateway (HTTP API) | 9.07 | 19.57 |  |
| AWS Lambda | 8.82 | 19.00 |  |
| RDS storage 50 GB gp3 Multi-AZ | 13.10 | 13.10 |  |
| CloudFront | 0.00 | 12.77 |  |
| SES | 6.40 | 10.40 |  |
| CloudWatch Logs | 4.10 | 9.03 | yes |
| AWS Backup (RDS + DynamoDB) | 7.22 | 7.22 | yes |
| CloudWatch alarms + dashboard | 4.20 | 4.20 |  |
| X-Ray | 1.66 | 4.16 |  |
| KMS (1 CMK + requests) | 1.84 | 2.74 | yes |
| Route 53 | 1.30 | 2.10 |  |
| Inter-AZ data transfer | 0.60 | 1.20 | yes |
| SQS | 0.20 | 0.80 |  |
| Secrets Manager | 0.40 | 0.40 |  |
| Data transfer out (S3 downloads) | 0.00 | 0.00 | yes |
| Cognito (8,400 MAU, Essentials free tier) | 0.00 | 0.00 |  |
| **Total** | **310.44** | **396.02** | |

Annual (10 normal + 2 exam): 3,896.41 USD | average 324.70 USD/month | 0.49 USD per student per year

Saving from all optimisations: 1,021.76 USD/year

  cf_downloads   saves   498.41 USD/year
  rds_ri         saves   363.67 USD/year
  lean_logs      saves    92.10 USD/year
  s3_gir90       saves    67.58 USD/year

