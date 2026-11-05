import { clearComposeMarker, runCompose, wasComposeStarted } from "./docker";

export default function globalTeardown(): void {
  if (!wasComposeStarted()) return;

  try {
    runCompose(["stop", "backend", "db", "redis"]);
  } finally {
    clearComposeMarker();
  }
}
