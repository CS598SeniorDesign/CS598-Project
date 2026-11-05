import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const repositoryRoot = path.resolve(__dirname, "../..");
export const setupMarker = path.join(
  os.tmpdir(),
  "questlog-e2e-docker-started",
);
export const composeArguments = ["compose", "-f", "docker-compose.yml"];

function ensureDockerEnvFile(): void {
  const envFile = path.join(repositoryRoot, ".env");

  if (!fs.existsSync(envFile)) {
    fs.copyFileSync(path.join(repositoryRoot, ".env.example"), envFile);
  }
}

export function runCompose(args: string[]): void {
  ensureDockerEnvFile();

  execFileSync("docker", [...composeArguments, ...args], {
    cwd: repositoryRoot,
    env: {
      ...process.env,
      DOCKER_DEBUG: "True",
      CSRF_TRUSTED_ORIGINS: "http://localhost:3000,http://localhost:3100",
    },
    stdio: "inherit",
  });
}

export function markComposeStarted(): void {
  fs.writeFileSync(setupMarker, "");
}

export function wasComposeStarted(): boolean {
  return fs.existsSync(setupMarker);
}

export function clearComposeMarker(): void {
  fs.rmSync(setupMarker, { force: true });
}
