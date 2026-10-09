import { notFound, redirect } from "next/navigation";
import { connection } from "next/server";
import { FeatureName, isFeatureEnabled } from "@/lib/featureFlags";

/**
 * Blocks a route when its feature flag is off. Call it from a server
 * component, such as the route's layout.
 *
 * Awaiting connection() renders the route per request, so the flag is read
 * when the request arrives rather than baked in at build time. Toggling a flag
 * therefore only needs a container restart, not a rebuild.
 *
 * @param feature - The flag guarding the route.
 * @param fallbackPath - Where to send users when the flag is off. Without
 *   one, the route responds with 404 so it appears not to exist.
 */
export async function requireFeature(
  feature: FeatureName,
  fallbackPath?: string,
): Promise<void> {
  await connection();

  if (isFeatureEnabled(feature)) {
    return;
  }

  if (fallbackPath) {
    redirect(fallbackPath);
  }

  notFound();
}
