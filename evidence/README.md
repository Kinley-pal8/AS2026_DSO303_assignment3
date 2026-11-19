# Evidence

| File | What it shows | Status |
| --- | --- | --- |
| `calculator-normal.csv` / `.pdf` | AWS Pricing Calculator: normal month, Singapore | **To add**: follow [`../docs/pricing-calculator-guide.md`](../docs/pricing-calculator-guide.md) |
| `calculator-exam.csv` / `.pdf` | AWS Pricing Calculator: exam month, Singapore | **To add** |
| `calculator-baseline.csv` | Assignment 2 design (before optimisation), for the savings | **To add** |
| [`cost-model-output.md`](cost-model-output.md) | Output of `scripts/cost_model.py`: every service, both profiles, both Regions | Done |
| [`price-sources.md`](price-sources.md) | Where each price came from and when it was checked | Done |
| [`latency-from-bhutan.txt`](latency-from-bhutan.txt) | Measured TCP connect time from Bhutan to Singapore, Mumbai and N. Virginia | Done |
| [`load-test-run1-t4g-micro.json`](load-test-run1-t4g-micro.json) | Load test run 1 (512 MB), measured by the client: 10 starts/s, 99 saves/s, 0 errors | Done |
| [`load-test-run2-after-fix.json`](load-test-run2-after-fix.json) | Load test run 2 (fix E, 1,769 MB) | Done |
| [`load-test-run1a-before-logging.json`](load-test-run1a-before-logging.json) | An earlier valid run 1, made before the Lambda REPORT lines were switched on. Renamed afterwards, so its internal label still says `run1-t4g-micro` | Done |
| [`cloudwatch-run1-t4g-micro.md`](cloudwatch-run1-t4g-micro.md), [`cloudwatch-run2-after-fix.md`](cloudwatch-run2-after-fix.md) | CloudWatch metrics, Logs Insights (cold starts, database connect time) and slow requests from the access log, for each run's window (written by `scripts/cloudwatch_summary.py`) | Done |
| `cw-run1-dashboard.png`, `cw-run2-dashboard.png` | Dashboard screenshots for the same windows: run 1 21:45–21:53 UTC, run 2 22:21–22:29 UTC, 19 Nov 2026 | **To add** |
| [`az-failover.log`](az-failover.log) | Failure test 1: three forced RDS failovers, API outage ≤ 17 s (measured on the deployed platform, 19 Nov 2026) | Done |
| `failure-2-*.png`, `failure-3-*.png`, `failure-4-*.png` | Failure tests 2–4 | **To add** (see [`../infra/failure-tests.md`](../infra/failure-tests.md)) |
