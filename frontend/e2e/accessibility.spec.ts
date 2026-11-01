import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const pages = [
  { name: "landing", path: "/" },
  { name: "signup", path: "/signup" },
  { name: "login", path: "/login" },
  { name: "catalog search", path: "/games/search" },
  { name: "library", path: "/library" },
];

for (const pageDefinition of pages) {
  test(`${pageDefinition.name} has no serious accessibility violations`, async ({
    page,
  }) => {
    await page.goto(pageDefinition.path);

    const results = await new AxeBuilder({ page }).analyze();

    expect(
      results.violations.filter((violation) =>
        ["serious", "critical"].includes(violation.impact ?? ""),
      ),
    ).toEqual([]);
  });
}

test("primary controls are keyboard reachable", async ({ page }) => {
  await page.goto("/login");

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "QuestLog" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Login" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Sign Up", exact: true }).first(),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByPlaceholder("Email")).toBeFocused();
});
