/**
 * Environment-driven feature flags for hiding incomplete features in staging
 * and production.
 *
 * Each flag reads a server-only FEATURE_<NAME> variable that must be exactly
 * "true" to enable it, so a missing or misspelled variable keeps the feature
 * hidden. Read flags from server code only (see requireFeature); these
 * variables are not exposed to the browser.
 *
 * Example usage
import { requireFeature } from "@/lib/requireFeature";

 export default async function AnalyticsLayout({
   children,
 }: {
   children: React.ReactNode;
 }) {
   await requireFeature("analytics");
   return children;
 }
 */
export const FEATURE_FLAGS = {
  analytics: "FEATURE_ANALYTICS",
  mfaSetup: "FEATURE_MFA_SETUP",
} as const;

export type FeatureName = keyof typeof FEATURE_FLAGS;

export function isFeatureEnabled(feature: FeatureName): boolean {
  return process.env[FEATURE_FLAGS[feature]] === "true";
}
