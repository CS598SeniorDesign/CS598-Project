import { expect, test } from "@playwright/test";

test.describe("primary user journeys", () => {
  test("landing page provides signup and login entry points", async ({
    page,
  }) => {
    await page.goto("/");

    await expect(page.getByRole("link", { name: "QuestLog" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Login" })).toHaveAttribute(
      "href",
      "/login",
    );
    await expect(page.getByRole("link", { name: "Sign Up" })).toHaveAttribute(
      "href",
      "/signup",
    );
  });

  test("signup prevents blank submission and displays backend errors", async ({
    page,
  }) => {
    await page.goto("/signup");

    await expect(page.getByPlaceholder("Email")).toHaveAttribute(
      "required",
      "",
    );
    await expect(page.getByPlaceholder("Password")).toHaveAttribute(
      "required",
      "",
    );
    await page.getByPlaceholder("Email").fill("existing@example.com");
    await page.getByPlaceholder("Password").fill("Password123!");

    await page.getByRole("button", { name: "Sign Up" }).click();
    await expect(page.locator('p[role="alert"]')).toHaveText(
      "An account with this email already exists.",
    );
  });

  test("login reports invalid credentials", async ({ page }) => {
    await page.goto("/login");

    await page.getByPlaceholder("Email").fill("unknown@example.com");
    await page.getByPlaceholder("Password").fill("wrong-password");
    await expect(page.getByPlaceholder("Email")).toHaveValue(
      "unknown@example.com",
    );
    await expect(page.getByPlaceholder("Password")).toHaveValue(
      "wrong-password",
    );
    await page.getByRole("button", { name: "Sign In" }).click();

    await expect(page.locator('p[role="alert"]')).toHaveText(
      "Unable to sign in. Check your email and password, or verify your account.",
    );
  });

  test("catalog search renders results and supports clearing", async ({
    page,
  }) => {
    await page.goto("/games/search");
    await page.getByPlaceholder("Search games...").fill("Catan");
    await expect(page.getByRole("button", { name: "Search" })).toBeEnabled();
    await page.getByRole("button", { name: "Search" }).click();

    await expect(page.getByRole("heading", { name: "Catan" })).toBeVisible();
    await page.getByRole("button", { name: "Clear" }).click();
    await expect(
      page.getByText("Ready to find your next favorite game?"),
    ).toBeVisible();
  });

  test("authenticated users can log a play through the real API", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.getByPlaceholder("Email").fill("demo@questlog.local");
    await page.getByPlaceholder("Password").fill("password123");
    await page.getByRole("button", { name: "Sign In" }).click();
    await page.waitForURL(/\/(avatar-selection|library)/);

    await page.goto("/games/13");
    await expect(page.getByRole("heading", { name: "Catan" })).toBeVisible();
    await page.getByRole("button", { name: "Log Play" }).click();

    const dialog = page.getByRole("dialog", { name: "Log a Play" });
    await dialog.getByPlaceholder("Enter player name").fill("E2E Guest");
    await dialog.getByRole("button", { name: "Save Play" }).click();

    await expect(
      dialog.getByRole("status").getByText(
        "Your play session was saved successfully!",
      ),
    ).toBeVisible();
    await dialog.getByRole("button", { name: "Done" }).click();
    await expect(dialog).toBeHidden();
  });

  test("library filtering shows an empty state for unmatched games", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.getByPlaceholder("Email").fill("demo@questlog.local");
    await page.getByPlaceholder("Password").fill("password123");
    await page.getByRole("button", { name: "Sign In" }).click();
    await page.waitForURL(/\/(avatar-selection|library)/);

    await page.goto("/library");
    const searchInput = page.getByPlaceholder("Search your collection...");
    await searchInput.fill("not a game");
    await expect(searchInput).toHaveValue("not a game");

    await expect(
      page.getByText(/No games found|No games match your search\./),
    ).toBeVisible();
  });
});
