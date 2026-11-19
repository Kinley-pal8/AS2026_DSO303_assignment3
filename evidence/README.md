# Evidence

| File | What it shows | Status |
| --- | --- | --- |
| `calculator-normal.csv` / `.pdf` | AWS Pricing Calculator: normal month, Singapore | **To add**: follow [`../docs/pricing-calculator-guide.md`](../docs/pricing-calculator-guide.md) |
| `calculator-exam.csv` / `.pdf` | AWS Pricing Calculator: exam month, Singapore | **To add** |
| `calculator-baseline.csv` | Assignment 2 design (before optimisation), for the savings | **To add** |
| [`cost-model-output.md`](cost-model-output.md) | Output of `scripts/cost_model.py`: every service, both profiles, both Regions | Done |
| [`price-sources.md`](price-sources.md) | Where each price came from and when it was checked | Done |
| [`latency-from-bhutan.txt`](latency-from-bhutan.txt) | Measured TCP connect time from Bhutan to Singapore, Mumbai and N. Virginia | Done |
| `load-test-run1-*.json`, `load-test-run2-*.json` | Load-test results before and after the fix | **To add** (written by `scripts/load_test.py`) |
| `cw-run1-*.png`, `cw-run2-*.png` | CloudWatch graphs proving the bottleneck and the fix | **To add** |
| [`az-failover.log`](az-failover.log) | Failure test 1: three forced RDS failovers, API outage ≤ 17 s (measured on the deployed platform, 19 Nov 2026) | Done |
| `failure-2-*.png`, `failure-3-*.png`, `failure-4-*.png` | Failure tests 2–4 | **To add** (see [`../infra/failure-tests.md`](../infra/failure-tests.md)) |
