#!/usr/bin/env python3
"""UniExam cost model for Assignment 3.

Reproduces every number in docs/cost-report.md from two inputs:
  PRICES      - AWS public on-demand prices (Price List API, read 19 Nov 2026)
  WORKLOAD    - usage assumptions for a normal month and an exam month

Run:  python3 scripts/cost_model.py            (Singapore, baseline + optimised)
      python3 scripts/cost_model.py --markdown (tables used in the report)

Cross-check the totals against the AWS Pricing Calculator estimates in evidence/.
"""
import sys

HOURS = 730  # AWS bills a month as 730 hours

# --------------------------------------------------------------------------- prices (USD)
# Source: AWS Price List API, https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/<service>/current/<region>/index.json
# and the CloudFront price map used by calculator.aws. Publication dates 2026-11-04 .. 2026-11-18.
PRICES = {
    "ap-southeast-1": {  # Asia Pacific (Singapore)
        "lambda_gb_s_arm": 0.0000133334, "lambda_req": 0.20 / 1e6,
        "httpapi_req": 1.25 / 1e6,
        "rds_t4g_medium_maz_hr": 0.203, "rds_t4g_large_maz_hr": 0.406, "rds_m7g_large_maz_hr": 0.468,
        "rds_t4g_medium_maz_ri1y_partial": (668, 0.0762),  # upfront USD, hourly USD (1-yr partial upfront)
        "rds_gp3_maz_gb": 0.276, "rds_backup_gb": 0.095,
        "rds_proxy_vcpu_hr": 0.018,
        "aurora_sv2_acu_hr": 0.20,
        "ddb_wru": 0.71 / 1e6, "ddb_rru": 0.1425 / 1e6, "ddb_storage_gb": 0.285, "ddb_pitr_gb": 0.228, "ddb_backup_gb": 0.114,
        "nat_hr": 0.059, "nat_gb": 0.059, "public_ipv4_hr": 0.005,
        "vpce_if_hr": 0.013, "vpce_gb": 0.01,
        "s3_std_gb": 0.025, "s3_ia_gb": 0.0138, "s3_gir_gb": 0.005, "s3_gda_gb": 0.002,
        "s3_put": 0.005 / 1000, "s3_get": 0.004 / 10000,
        "dto_internet_gb": 0.12,             # S3/EC2/API data transfer out to the internet, first 10 TB
        "cf_dto_gb": 0.109, "cf_https_req": 0.012 / 10000,  # CloudFront India edge (nearest to Bhutan)
        "waf_acl": 5.0, "waf_rule": 1.0, "waf_req": 0.60 / 1e6,
        "cw_logs_ingest_gb": 0.70, "cw_logs_store_gb": 0.03, "cw_alarm": 0.10, "cw_dashboard": 3.0,
        "xray_trace": 5.0 / 1e6,
        "kms_key": 1.0, "kms_req": 0.03 / 10000,
        "secret": 0.40,
        "sqs_req": 0.40 / 1e6,
        "ses_email": 0.10 / 1000,
        "inter_az_gb": 0.02,                 # 0.01 out + 0.01 in
        "route53_zone": 0.50, "route53_query": 0.40 / 1e6,
    },
    "ap-south-1": {  # Asia Pacific (Mumbai) - comparison Region
        "lambda_gb_s_arm": 0.0000133334, "lambda_req": 0.20 / 1e6,
        "httpapi_req": 1.05 / 1e6,
        "rds_t4g_medium_maz_hr": 0.167, "rds_t4g_large_maz_hr": 0.334, "rds_m7g_large_maz_hr": 0.48,
        "rds_t4g_medium_maz_ri1y_partial": (550, 0.0627),  # scaled from Singapore ratio; confirm in calculator
        "rds_gp3_maz_gb": 0.262, "rds_backup_gb": 0.095,
        "rds_proxy_vcpu_hr": 0.017,
        "aurora_sv2_acu_hr": 0.18,
        "ddb_wru": 0.71 / 1e6, "ddb_rru": 0.1425 / 1e6, "ddb_storage_gb": 0.285, "ddb_pitr_gb": 0.228, "ddb_backup_gb": 0.114,
        "nat_hr": 0.056, "nat_gb": 0.056, "public_ipv4_hr": 0.005,
        "vpce_if_hr": 0.011, "vpce_gb": 0.01,
        "s3_std_gb": 0.025, "s3_ia_gb": 0.0138, "s3_gir_gb": 0.005, "s3_gda_gb": 0.002,
        "s3_put": 0.005 / 1000, "s3_get": 0.004 / 10000,
        "dto_internet_gb": 0.1093,
        "cf_dto_gb": 0.109, "cf_https_req": 0.012 / 10000,
        "waf_acl": 5.0, "waf_rule": 1.0, "waf_req": 0.60 / 1e6,
        "cw_logs_ingest_gb": 0.67, "cw_logs_store_gb": 0.03, "cw_alarm": 0.10, "cw_dashboard": 3.0,
        "xray_trace": 5.0 / 1e6,
        "kms_key": 1.0, "kms_req": 0.03 / 10000,
        "secret": 0.40,
        "sqs_req": 0.40 / 1e6,
        "ses_email": 0.10 / 1000,
        "inter_az_gb": 0.02,
        "route53_zone": 0.50, "route53_query": 0.40 / 1e6,
    },
}

# --------------------------------------------------------------------------- workload
# Normal month: 300-500 concurrent users (400 average) for 12 h/day, one API call per user per minute.
# Exam month: normal traffic + 40,000 exam attempts (8,000 students x 5 exams), 2 h each,
#             autosave every 30 s (240 saves per attempt), peak 3,000 starts in 5 minutes.
NORMAL_API = 400 * 12 * 60 * 30          # 8.64 M requests
EXAM_ATTEMPTS = 8000 * 5
EXAM_API = NORMAL_API + EXAM_ATTEMPTS * (240 + 10)  # autosaves + start/submit/results calls
WORKLOAD = {
    "normal": {
        "api_requests": NORMAL_API, "lambda_ms": 120, "lambda_mb": 512,
        "async_invocations": 150_000, "async_ms": 300, "async_mb": 256,
        "ddb_wru": 8e6, "ddb_rru": 10e6, "ddb_gb": 5,
        "nat_gb": 20, "s3_new_gb": 320, "s3_puts": 32_000, "s3_download_gb": 480,
        "static_requests": 1e6, "static_gb": 50,
        "logs_gb": 15, "xray_sample": 0.05, "kms_requests": 300_000, "sqs_requests": 1.5e6,
        "emails": 64_000, "inter_az_gb": 30, "dns_queries": 2e6,
    },
    "exam": {
        "api_requests": EXAM_API, "lambda_ms": 120, "lambda_mb": 512,
        "async_invocations": 300_000, "async_ms": 300, "async_mb": 256,
        "ddb_wru": 8e6 + EXAM_ATTEMPTS * 240 * 4, "ddb_rru": 25e6, "ddb_gb": 8,   # 4 KB answer item = 4 WRU per save
        "nat_gb": 40, "s3_new_gb": 320, "s3_puts": 32_000, "s3_download_gb": 480,
        "static_requests": 2e6, "static_gb": 100,
        "logs_gb": 33, "xray_sample": 0.05, "kms_requests": 600_000, "sqs_requests": 3e6,
        "emails": 104_000, "inter_az_gb": 60, "dns_queries": 4e6,
    },
}

STUDENTS = 8000


def s3_storage_year1(p, new_gb, gir_month=6):
    """Average monthly S3 storage cost in year 1 with the lifecycle rules (Std 30d -> IA -> GIR (180d, or 90d optimised) -> GDA 365d)."""
    total = 0.0
    for month in range(1, 13):
        cost = 0.0
        for age in range(month):            # data uploaded `age` months ago
            gb = new_gb
            if age < 1:
                cost += gb * p["s3_std_gb"]
            elif age < gir_month:
                cost += gb * p["s3_ia_gb"]
            elif age < 12:
                cost += gb * p["s3_gir_gb"]
            else:
                cost += gb * p["s3_gda_gb"]
        total += cost
    return total / 12


def month_cost(region, profile, opt):
    """Cost per service for one month. opt = set of optimisation names applied."""
    p, w = PRICES[region], WORKLOAD[profile]
    c = {}
    # --- compute and API
    gb_s = w["api_requests"] * w["lambda_ms"] / 1000 * w["lambda_mb"] / 1024
    gb_s += w["async_invocations"] * w["async_ms"] / 1000 * w["async_mb"] / 1024
    c["AWS Lambda"] = gb_s * p["lambda_gb_s_arm"] + (w["api_requests"] + w["async_invocations"]) * p["lambda_req"]
    c["API Gateway (HTTP API)"] = w["api_requests"] * p["httpapi_req"]
    # --- database
    if "rds_ri" in opt:
        upfront, hourly = p["rds_t4g_medium_maz_ri1y_partial"]
        c["RDS PostgreSQL Multi-AZ (db.t4g.medium)"] = upfront / 12 + hourly * HOURS
    else:
        c["RDS PostgreSQL Multi-AZ (db.t4g.medium)"] = p["rds_t4g_medium_maz_hr"] * HOURS
    c["RDS storage 50 GB gp3 Multi-AZ"] = 50 * p["rds_gp3_maz_gb"]
    c["RDS Proxy (2 vCPU)"] = 2 * p["rds_proxy_vcpu_hr"] * HOURS
    c["DynamoDB on-demand"] = (w["ddb_wru"] * p["ddb_wru"] + w["ddb_rru"] * p["ddb_rru"]
                               + max(0, w["ddb_gb"] - 25) * p["ddb_storage_gb"] + w["ddb_gb"] * p["ddb_pitr_gb"])
    # --- network
    c["NAT gateways (2) + public IPv4"] = 2 * HOURS * (p["nat_hr"] + p["public_ipv4_hr"]) + w["nat_gb"] * p["nat_gb"]
    c["Inter-AZ data transfer"] = w["inter_az_gb"] * p["inter_az_gb"]
    # --- storage and delivery
    c["S3 uploads (lifecycle, year-1 avg)"] = s3_storage_year1(p, w["s3_new_gb"], 3 if "s3_gir90" in opt else 6) + w["s3_puts"] * p["s3_put"]
    cf_requests = w["api_requests"] + w["static_requests"]
    cf_gb = w["static_gb"] + w["api_requests"] * 2 / 1e6   # ~2 KB per API response
    if "cf_downloads" in opt:
        cf_gb += w["s3_download_gb"]
        c["Data transfer out (S3 downloads)"] = 0.0
    else:
        c["Data transfer out (S3 downloads)"] = max(0, w["s3_download_gb"] - 100) * p["dto_internet_gb"]  # 100 GB global free tier
    c["CloudFront"] = max(0, cf_gb - 1024) * p["cf_dto_gb"] + max(0, cf_requests - 10e6) * p["cf_https_req"]  # always-free 1 TB, 10 M req
    c["AWS WAF"] = p["waf_acl"] + 4 * p["waf_rule"] + cf_requests * p["waf_req"]
    # --- operations
    logs_gb = w["logs_gb"] * (0.4 if "lean_logs" in opt else 1.0)
    retention_days = 14 if "lean_logs" in opt else 30
    c["CloudWatch Logs"] = logs_gb * p["cw_logs_ingest_gb"] + logs_gb * retention_days / 30 * p["cw_logs_store_gb"]
    c["CloudWatch alarms + dashboard"] = 12 * p["cw_alarm"] + p["cw_dashboard"]
    sample = w["xray_sample"]
    c["X-Ray"] = max(0, w["api_requests"] * sample - 100_000) * p["xray_trace"]
    c["KMS (1 CMK + requests)"] = p["kms_key"] + max(0, w["kms_requests"] - 20_000) * p["kms_req"]
    c["Secrets Manager"] = p["secret"]
    c["SQS"] = max(0, w["sqs_requests"] - 1e6) * p["sqs_req"]
    c["SES"] = w["emails"] * p["ses_email"]
    c["AWS Backup (RDS + DynamoDB)"] = 40 * p["rds_backup_gb"] + 30 * p["ddb_backup_gb"]
    c["Route 53"] = p["route53_zone"] + w["dns_queries"] * p["route53_query"]
    c["Cognito (8,400 MAU, Essentials free tier)"] = 0.0
    return c


HIDDEN = {"Data transfer out (S3 downloads)", "NAT gateways (2) + public IPv4", "CloudWatch Logs",
          "KMS (1 CMK + requests)", "AWS Backup (RDS + DynamoDB)", "Inter-AZ data transfer"}
OPTIMISATIONS = ["cf_downloads", "rds_ri", "lean_logs", "s3_gir90"]


def summary(region, opt):
    n, e = month_cost(region, "normal", opt), month_cost(region, "exam", opt)
    annual = 10 * sum(n.values()) + 2 * sum(e.values())
    return n, e, annual


def table(region, opt, md):
    n, e, annual = summary(region, opt)
    rows = sorted(n, key=lambda k: -e[k])
    if md:
        print("| Service | Normal month (USD) | Exam month (USD) | Hidden cost? |")
        print("| --- | ---: | ---: | --- |")
        for k in rows:
            print(f"| {k} | {n[k]:,.2f} | {e[k]:,.2f} | {'yes' if k in HIDDEN else ''} |")
        print(f"| **Total** | **{sum(n.values()):,.2f}** | **{sum(e.values()):,.2f}** | |")
    else:
        for k in rows:
            print(f"  {k:<45} {n[k]:>9.2f} {e[k]:>9.2f}")
        print(f"  {'TOTAL':<45} {sum(n.values()):>9.2f} {sum(e.values()):>9.2f}")
    print(f"\nAnnual (10 normal + 2 exam): {annual:,.2f} USD | average {annual / 12:,.2f} USD/month | "
          f"{annual / STUDENTS:,.2f} USD per student per year\n")
    return annual


if __name__ == "__main__":
    md = "--markdown" in sys.argv
    print(f"Workload: normal {NORMAL_API / 1e6:.2f} M API requests, exam {EXAM_API / 1e6:.2f} M\n")
    for region in ("ap-southeast-1", "ap-south-1"):
        print(f"## {region} - baseline (Assignment 2 design)\n")
        base = table(region, set(), md)
        print(f"## {region} - optimised\n")
        best = table(region, set(OPTIMISATIONS), md)
        print(f"Saving from all optimisations: {base - best:,.2f} USD/year\n")
        for o in OPTIMISATIONS:
            _, _, a = summary(region, {o})
            print(f"  {o:<14} saves {base - a:>8,.2f} USD/year")
        print()
