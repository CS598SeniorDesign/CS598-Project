import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    health_load: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 10),
      duration: __ENV.DURATION || "30s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    checks: ["rate>0.99"],
  },
};

const baseUrl = (__ENV.BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export default function () {
  const responses = http.batch([
    ["GET", `${baseUrl}/health/`],
    ["GET", `${baseUrl}/ready/`],
  ]);

  check(responses[0], {
    "liveness responds with 200": (response) => response.status === 200,
  });
  check(responses[1], {
    "readiness responds with 200": (response) => response.status === 200,
  });

  sleep(1);
}
