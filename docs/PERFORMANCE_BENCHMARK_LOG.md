# Performance Benchmark Execution Log

## Scope

This benchmark measures the public Django liveness and readiness endpoints
under sustained concurrent load. It records request throughput, failure rate,
and response-latency percentiles without requiring authenticated user data.

The executable scenario is [health-load.js](../performance/k6/health-load.js).

## Workload

| Parameter | Default |
| --- | --- |
| Virtual users | 10 |
| Duration | 30 seconds |
| Requests per iteration | 2 (`/health/`, `/ready/`) |
| Target | `http://localhost:8000` |
| Failure threshold | Less than 1% |
| p95 latency threshold | Less than 500 ms |
| p99 latency threshold | Less than 1,000 ms |

## Execution

Start the backend stack first, verify both health endpoints, then run:

```bash
k6 run --summary-export=performance/k6/results.json performance/k6/health-load.js
```

### Windows with Docker Compose

From the repository root, start the services required by the benchmark:

```powershell
docker compose up -d db redis backend
```

Wait for the backend to finish starting, then verify both endpoints:

```powershell
curl.exe http://localhost:8000/health/
curl.exe http://localhost:8000/ready/
```

Both requests should return a successful response before running k6:

```powershell
k6 run --summary-export=performance/k6/results.json performance/k6/health-load.js
```

Use `curl.exe` rather than `curl` in PowerShell because `curl` is an alias for
PowerShell's `Invoke-WebRequest`.

For a different target or workload:

```bash
k6 run \
  -e BASE_URL=http://staging.example.com \
  -e VUS=25 \
  -e DURATION=2m \
  --summary-export=performance/k6/results.json \
  performance/k6/health-load.js
```

## Results

| Run date | Target | VUs | Duration | Throughput | p95 | p99 | Error rate | Status |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| 2026-11-01 | Local Docker backend (`localhost:8000`) | 10 | 30s | 19.38 req/s | 45.08 ms | Not reported by summary output; max 113.35 ms | 0.00% | Passed |

The run completed 300 iterations and 600 total requests, with 600 successful
checks and no failed requests. The p99 value was not printed in the captured
summary; the observed maximum request duration was 113.35 ms. The configured
thresholds passed during execution. These values are baseline measurements for
the local Docker environment, not a production capacity guarantee.
