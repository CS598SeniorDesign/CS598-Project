import { request } from "@playwright/test";

import { markComposeStarted, runCompose } from "./docker";

async function waitForBackend(): Promise<void> {
  const context = await request.newContext();

  try {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      try {
        const response = await context.get("http://127.0.0.1:8000/ready/");
        if (response.ok()) return;
      } catch {
        // The backend may still be starting.
      }

      await new Promise((resolve) => setTimeout(resolve, 2_000));
    }
  } finally {
    await context.dispose();
  }

  throw new Error("Docker-backed backend did not become ready within 120 seconds.");
}

export default async function globalSetup(): Promise<void> {
  runCompose(["up", "--build", "-d", "db", "redis", "backend"]);
  markComposeStarted();
  await waitForBackend();
  runCompose(["exec", "-T", "backend", "python", "manage.py", "seed_e2e"]);
}
