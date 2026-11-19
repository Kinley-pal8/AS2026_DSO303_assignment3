# CloudWatch summary: run2-after-fix

Window (UTC): 2026-11-19T22:22:30+00:00 to 2026-11-19T22:28:02+00:00, padded by 1 minute each side.
Resources: API 94y5wgeidd, Lambda uniexam-prod-api, RDS uniexam-prod-db, DynamoDB uniexam-prod-attempts.

## Metrics

| Metric | Statistic | Value |
| --- | --- | ---: |
| API Gateway requests | Sum, sum of 1-min values | 30,299.0 |
| API Gateway latency p95 (ms) | p95, max of 1-min values | 40.8 |
| API Gateway latency p99 (ms) | p99, max of 1-min values | 106.6 |
| API Gateway 5xx | Sum, sum of 1-min values | 0.0 |
| API Gateway 4xx | Sum, sum of 1-min values | 0.0 |
| Lambda concurrent executions | Maximum, max of 1-min values | 13.0 |
| Lambda duration p95 (ms) | p95, max of 1-min values | 12.9 |
| Lambda duration p99 (ms) | p99, max of 1-min values | 66.2 |
| Lambda duration max (ms) | Maximum, max of 1-min values | 556.5 |
| Lambda throttles | Sum, sum of 1-min values | 0.0 |
| Lambda errors | Sum, sum of 1-min values | 0.0 |
| RDS CPU (%) | Maximum, max of 1-min values | 5.6 |
| RDS CPU credit balance | Minimum, min of 1-min values | 76.7 |
| RDS connections | Maximum, max of 1-min values | 13.0 |
| RDS read latency (s) | Maximum, max of 1-min values | 0.0 |
| RDS write latency (s) | Maximum, max of 1-min values | 0.1 |
| RDS freeable memory (bytes) | Minimum, min of 1-min values | 165,548,032.0 |
| DynamoDB write units consumed | Sum, sum of 1-min values | 30,298.0 |
| DynamoDB UpdateItem latency (ms) | Average, max of 1-min values | 3.5 |
| DynamoDB PutItem latency (ms) | Average, max of 1-min values | 3.7 |
| DynamoDB throttled requests | Sum, sum of 1-min values | no data |

## Lambda REPORT lines (cold starts)

```
[
  {
    "invocations": "30299",
    "cold_starts": "13",
    "avg_init_ms": "728.5015",
    "max_init_ms": "842.528",
    "p95_duration_ms": "11.4173",
    "max_duration_ms": "556.555"
  }
]
```

## New database connections (db_connect lines from backend/db.py)

```
[
  {
    "new_db_connections": "13",
    "avg_connect_ms": "208.2308",
    "max_connect_ms": "239",
    "avg_schema_ms": "16.6154",
    "max_schema_ms": "30"
  }
]
```

## Cold starts and p99 duration per 30 seconds

```
[
  {
    "bin(30s)": "2026-11-19 22:22:00.000",
    "cold_starts": "1",
    "p99_duration_ms": "276.893"
  },
  {
    "bin(30s)": "2026-11-19 22:22:30.000",
    "cold_starts": "2",
    "p99_duration_ms": "17.4366"
  },
  {
    "bin(30s)": "2026-11-19 22:23:00.000",
    "cold_starts": "8",
    "p99_duration_ms": "15.4138"
  },
  {
    "bin(30s)": "2026-11-19 22:23:30.000",
    "p99_duration_ms": "16.223"
  },
  {
    "bin(30s)": "2026-11-19 22:24:00.000",
    "p99_duration_ms": "17.3077"
  },
  {
    "bin(30s)": "2026-11-19 22:24:30.000",
    "cold_starts": "1",
    "p99_duration_ms": "17.9056"
  },
  {
    "bin(30s)": "2026-11-19 22:25:00.000",
    "p99_duration_ms": "16.8639"
  },
  {
    "bin(30s)": "2026-11-19 22:25:30.000",
    "p99_duration_ms": "15.8511"
  },
  {
    "bin(30s)": "2026-11-19 22:26:00.000",
    "cold_starts": "1",
    "p99_duration_ms": "18.6729"
  },
  {
    "bin(30s)": "2026-11-19 22:26:30.000",
    "p99_duration_ms": "15.7564"
  },
  {
    "bin(30s)": "2026-11-19 22:27:00.000",
    "p99_duration_ms": "14.9887"
  },
  {
    "bin(30s)": "2026-11-19 22:27:30.000",
    "p99_duration_ms": "15.0788"
  }
]
```

## Requests that took 300 ms or more (API Gateway access log)

```
[
  {
    "method": "PUT",
    "requests_over_300ms": "10",
    "max_ms": "1150"
  },
  {
    "method": "POST",
    "requests_over_300ms": "3",
    "max_ms": "1166"
  }
]
```

Slowest 20:

```
[
  {
    "@timestamp": "2026-11-19 22:22:18.966",
    "method": "POST",
    "status": "200",
    "latencyMs": "1166",
    "@ptr": "CqwBCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjUaGAIGrvCyOQAAAAASFIMQAAav92WQAAAHkiABKNaana+fNDDaxJ6vnzQ4B0DJDUiTGlC4EBAAGAE="
  },
  {
    "@timestamp": "2026-11-19 22:23:00.130",
    "method": "PUT",
    "status": "200",
    "latencyMs": "1150",
    "@ptr": "Cq4BCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjcaGAIGp0y0QQAAAAFAAp/oAAav92nQAAAAEiABKJ7zna+fNDDNwqGvnzQ46gFAgtIDSPx2UJhtEFgYAQ=="
  },
  {
    "@timestamp": "2026-11-19 22:23:00.450",
    "method": "PUT",
    "status": "200",
    "latencyMs": "1117",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGpqSwbQAAAACnIFpSAAav92mAAAAE0iABKOL0na+fNDCeraOvnzQ4pQNAq8YGSN6vAVD4pQEQngEYAQ=="
  },
  {
    "@timestamp": "2026-11-19 22:23:00.288",
    "method": "PUT",
    "status": "200",
    "latencyMs": "1017",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGrhY3MwAAAAAlXtM3AAav92eAAAABMiABKMbyna+fNDCJw6GvnzQ4tAJAouUESICQAVCbhgEQPRgB"
  },
  {
    "@timestamp": "2026-11-19 22:23:01.268",
    "method": "PUT",
    "status": "200",
    "latencyMs": "962",
    "@ptr": "Cq4BCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjcaGAIGp0y0QQAAAAFAAp/oAAav92nQAAAAEiABKJ7zna+fNDDNwqGvnzQ46gFAgtIDSPx2UJhtEDwYAQ=="
  },
  {
    "@timestamp": "2026-11-19 22:23:01.154",
    "method": "PUT",
    "status": "200",
    "latencyMs": "938",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGr81z+QAAAAACYJ/tAAav92uAAAADkiABKKH1na+fNDDilqWvnzQ45gdA+cMPSISyAlCbqAIQ/AEYAQ=="
  },
  {
    "@timestamp": "2026-11-19 22:23:00.534",
    "method": "PUT",
    "status": "200",
    "latencyMs": "919",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGqs17qwAAAACI0u83AAav92rQAAAEsiABKPPyna+fNDChyKSvnzQ42wZAia8NSLSVAlDOiwIQHxgB"
  },
  {
    "@timestamp": "2026-11-19 22:23:00.875",
    "method": "PUT",
    "status": "200",
    "latencyMs": "870",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGrh8BWAAAAABLRRTrAAav923AAAAAgiABKJ3Enq+fNDCTgaevnzQ4qwtAzMoWSOOJA1D6/wIQrAEYAQ=="
  },
  {
    "@timestamp": "2026-11-19 22:23:00.499",
    "method": "PUT",
    "status": "200",
    "latencyMs": "823",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGrh8BWAAAAABLRRTrAAav923AAAAAgiABKJ3Enq+fNDCTgaevnzQ4qwtAzMoWSOOJA1D6/wIQRxgB"
  },
  {
    "@timestamp": "2026-11-19 22:26:25.589",
    "method": "PUT",
    "status": "200",
    "latencyMs": "568",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGrvCyOQAAAAASFV6TAAav93PgAAAHkiABKPORpK+fNDCNhq2vnzQ4mwpA56sUSPHmAlCJ3QIQjwoYAQ=="
  },
  {
    "@timestamp": "2026-11-19 22:22:31.685",
    "method": "POST",
    "status": "200",
    "latencyMs": "344",
    "@ptr": "Cq4BCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjcaGAIGp0y0QQAAAAFAAp/oAAav92nQAAAAEiABKJ7zna+fNDDNwqGvnzQ46gFAgtIDSPx2UJhtEAoYAQ=="
  },
  {
    "@timestamp": "2026-11-19 22:22:51.179",
    "method": "POST",
    "status": "200",
    "latencyMs": "318",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGpqSwbQAAAACnIFpSAAav92mAAAAE0iABKOL0na+fNDCeraOvnzQ4pQNAq8YGSN6vAVD4pQEQhAEYAQ=="
  },
  {
    "@timestamp": "2026-11-19 22:26:22.593",
    "method": "PUT",
    "status": "200",
    "latencyMs": "312",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCJCcmq+fNBCX77WvnzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGr81z+QAAAAACYYAyAAav93qAAAADkiABKN7Zqq+fNDCTgrKvnzQ42ApAqqUVSN7vAlD25QIQ3QIYAQ=="
  }
]
```
