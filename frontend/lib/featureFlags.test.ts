import { isFeatureEnabled } from "./featureFlags";

describe("isFeatureEnabled", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it("is enabled when the variable is exactly true", () => {
    process.env.FEATURE_ANALYTICS = "true";

    expect(isFeatureEnabled("analytics")).toBe(true);
  });

  it("is disabled when the variable is missing", () => {
    delete process.env.FEATURE_ANALYTICS;

    expect(isFeatureEnabled("analytics")).toBe(false);
  });

  it.each(["false", "1", "TRUE", "yes", ""])(
    "is disabled for the value %p",
    (value) => {
      process.env.FEATURE_ANALYTICS = value;

      expect(isFeatureEnabled("analytics")).toBe(false);
    },
  );
});
