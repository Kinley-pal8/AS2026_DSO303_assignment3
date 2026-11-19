# CloudWatch summary: run1-t4g-micro

Window (UTC): 2026-11-19T21:46:28+00:00 to 2026-11-19T21:52:01+00:00, padded by 1 minute each side.
Resources: API 94y5wgeidd, Lambda uniexam-prod-api, RDS uniexam-prod-db, DynamoDB uniexam-prod-attempts.

## Metrics

| Metric | Statistic | Value |
| --- | --- | ---: |
| API Gateway requests | Sum, sum of 1-min values | 30,293.0 |
| API Gateway latency p95 (ms) | p95, max of 1-min values | 89.7 |
| API Gateway latency p99 (ms) | p99, max of 1-min values | 1,196.1 |
| API Gateway 5xx | Sum, sum of 1-min values | 0.0 |
| API Gateway 4xx | Sum, sum of 1-min values | 0.0 |
| Lambda concurrent executions | Maximum, max of 1-min values | 13.0 |
| Lambda duration p95 (ms) | p95, max of 1-min values | 14.3 |
| Lambda duration p99 (ms) | p99, max of 1-min values | 418.8 |
| Lambda duration max (ms) | Maximum, max of 1-min values | 473.7 |
| Lambda throttles | Sum, sum of 1-min values | 0.0 |
| Lambda errors | Sum, sum of 1-min values | 0.0 |
| RDS CPU (%) | Maximum, max of 1-min values | 6.4 |
| RDS CPU credit balance | Minimum, min of 1-min values | 72.4 |
| RDS connections | Maximum, max of 1-min values | 13.0 |
| RDS read latency (s) | Maximum, max of 1-min values | 0.0 |
| RDS write latency (s) | Maximum, max of 1-min values | 0.0 |
| RDS freeable memory (bytes) | Minimum, min of 1-min values | 168,247,296.0 |
| DynamoDB write units consumed | Sum, sum of 1-min values | 30,292.0 |
| DynamoDB UpdateItem latency (ms) | Average, max of 1-min values | 3.6 |
| DynamoDB PutItem latency (ms) | Average, max of 1-min values | 3.4 |
| DynamoDB throttled requests | Sum, sum of 1-min values | no data |

## Lambda REPORT lines (cold starts)

```
[
  {
    "invocations": "30293",
    "cold_starts": "13",
    "avg_init_ms": "812.8908",
    "max_init_ms": "1089.186",
    "p95_duration_ms": "12.2679",
    "max_duration_ms": "473.743"
  }
]
```

## New database connections (db_connect lines from backend/db.py)

```
[
  {
    "new_db_connections": "13",
    "avg_connect_ms": "309.2308",
    "max_connect_ms": "377",
    "avg_schema_ms": "18.2308",
    "max_schema_ms": "37"
  }
]
```

## Cold starts and p99 duration per 30 seconds

```
[
  {
    "bin(30s)": "2026-11-19 21:46:00.000",
    "cold_starts": "1",
    "p99_duration_ms": "329.237"
  },
  {
    "bin(30s)": "2026-11-19 21:46:30.000",
    "cold_starts": "2",
    "p99_duration_ms": "28.5976"
  },
  {
    "bin(30s)": "2026-11-19 21:47:00.000",
    "cold_starts": "7",
    "p99_duration_ms": "17.4465"
  },
  {
    "bin(30s)": "2026-11-19 21:47:30.000",
    "p99_duration_ms": "18.3401"
  },
  {
    "bin(30s)": "2026-11-19 21:48:00.000",
    "p99_duration_ms": "20.2265"
  },
  {
    "bin(30s)": "2026-11-19 21:48:30.000",
    "p99_duration_ms": "19.3567"
  },
  {
    "bin(30s)": "2026-11-19 21:49:00.000",
    "p99_duration_ms": "17.7986"
  },
  {
    "bin(30s)": "2026-11-19 21:49:30.000",
    "p99_duration_ms": "18.1578"
  },
  {
    "bin(30s)": "2026-11-19 21:50:00.000",
    "p99_duration_ms": "18.7103"
  },
  {
    "bin(30s)": "2026-11-19 21:50:30.000",
    "cold_starts": "1",
    "p99_duration_ms": "18.8981"
  },
  {
    "bin(30s)": "2026-11-19 21:51:00.000",
    "p99_duration_ms": "16.2033"
  },
  {
    "bin(30s)": "2026-11-19 21:51:30.000",
    "cold_starts": "2",
    "p99_duration_ms": "17.4814"
  }
]
```

## Requests that took 300 ms or more (API Gateway access log)

```
[
  {
    "method": "PUT",
    "requests_over_300ms": "10",
    "max_ms": "1494"
  },
  {
    "method": "POST",
    "requests_over_300ms": "3",
    "max_ms": "1450"
  }
]
```

Slowest 20:

```
[
  {
    "@timestamp": "2026-11-19 21:46:58.890",
    "method": "PUT",
    "status": "200",
    "latencyMs": "1494",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGpqSwbQAAAACnFTQOAAav9uJAAAAE0iABKOuGmq6fNDD39Z6unzQ48gRA2t4JSNLkAVDr2gEQhQEYAQ=="
  },
  {
    "@timestamp": "2026-11-19 21:46:15.367",
    "method": "POST",
    "status": "200",
    "latencyMs": "1450",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGrhY3MwAAAAAlVaj9AAav9uRAAAABMiABKMeTma6fNDDu36CunzQ45AZA2MANSKCZAlC4jwIQABgB"
  },
  {
    "@timestamp": "2026-11-19 21:46:58.894",
    "method": "PUT",
    "status": "200",
    "latencyMs": "1346",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGp0y0QQAAAAE/7Y1cAAav9uWwAAAAEiABKMaFmq6fNDDvkqCunzQ4oAVAw7oKSIDuAVCZ5AEQnQEYAQ=="
  },
  {
    "@timestamp": "2026-11-19 21:46:59.970",
    "method": "PUT",
    "status": "200",
    "latencyMs": "1229",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGrh8BWAAAAABLMONwAAav9uYwAAAAgiABKPGQmq6fNDClhqOunzQ4vglAtvISSL/fAlDX1QIQKhgB"
  },
  {
    "@timestamp": "2026-11-19 21:46:59.956",
    "method": "PUT",
    "status": "200",
    "latencyMs": "1176",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGqs17qwAAAACIwMcCAAav9uOgAAAEsiABKPeBmq6fNDDdkqCunzQ4jgdA1JQOSJ+hAlC3lwIQTBgB"
  },
  {
    "@timestamp": "2026-11-19 21:46:59.153",
    "method": "PUT",
    "status": "200",
    "latencyMs": "1134",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGr81z+QAAAAACWKPpAAav9uQgAAADkiABKML+ma6fNDCo4KCunzQ4iQhAyokQSM67AlDlsQIQ2wEYAQ=="
  },
  {
    "@timestamp": "2026-11-19 21:46:59.463",
    "method": "PUT",
    "status": "200",
    "latencyMs": "1102",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGrh8BWAAAAABLMONwAAav9uYwAAAAgiABKPGQmq6fNDClhqOunzQ4vglAtvISSL/fAlDX1QIQGhgB"
  },
  {
    "@timestamp": "2026-11-19 21:46:59.463",
    "method": "PUT",
    "status": "200",
    "latencyMs": "950",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGrh8BWAAAAABLMONwAAav9uYwAAAAgiABKPGQmq6fNDClhqOunzQ4vglAtvISSL/fAlDX1QIQ2wEYAQ=="
  },
  {
    "@timestamp": "2026-11-19 21:46:30.180",
    "method": "POST",
    "status": "200",
    "latencyMs": "773",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGr81z+QAAAAACWKPpAAav9uQgAAADkiABKML+ma6fNDCo4KCunzQ4iQhAyokQSM67AlDlsQIQFRgB"
  },
  {
    "@timestamp": "2026-11-19 21:46:40.181",
    "method": "POST",
    "status": "200",
    "latencyMs": "469",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGrPodTAAAAAA5QYT7AAav9uLwAAACwiABKJOBmq6fNDDp2Z2unzQ49QJA6eYFSP2iAVCYmQEQBhgB"
  },
  {
    "@timestamp": "2026-11-19 21:51:55.006",
    "method": "PUT",
    "status": "200",
    "latencyMs": "442",
    "@ptr": "Cq4BCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjcaGAIGpqSwbQAAAACnFw7pAAav9vjAAAAE0iABKNeurK6fNDCCja6unzQ4yQFAuZADSOZlUIRcELcBGAE="
  },
  {
    "@timestamp": "2026-11-19 21:51:55.004",
    "method": "PUT",
    "status": "200",
    "latencyMs": "419",
    "@ptr": "Cq4BCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjcaGAIGpqSwbQAAAACnFw7pAAav9vjAAAAE0iABKNeurK6fNDCCja6unzQ4yQFAuZADSOZlUIRcEHwYAQ=="
  },
  {
    "@timestamp": "2026-11-19 21:50:58.894",
    "method": "PUT",
    "status": "200",
    "latencyMs": "416",
    "@ptr": "CrABCnMKKTc2MTkyOTEyMTI5NzovYXdzL2FwaWdhdGV3YXkvdW5pZXhhbS1wcm9kEAAaJGYzZjZhZDhkLTE1NTQtNDYwMy1iNDdhLTk2MDI4NTQ2ZmE4MCIOCMChlq6fNBCv/LGunzQ41sOR6Zo0QLjumpqfNEgAEjkaGAIGrvCyOQAAAAASDX3kAAav9vGQAAAHkiABKIWGpa6fNDCRhK6unzQ4rwtA09IWSP2GA1CV/QIQhggYAQ=="
  }
]
```
