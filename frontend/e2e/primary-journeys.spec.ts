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
    const signupRequest = page.waitForRequest("**/auth/signup");

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

    await page.route("**/auth/session", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    });
    await page.context().addCookies([
      {
        name: "csrf_token",
        value: "e2e-token",
        url: "http://localhost:3000",
      },
    ]);
    await page.route("**/auth/signup", async (route) => {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({
          errors: [{ message: "An account with this email already exists." }],
        }),
      });
    });

    await page.getByRole("button", { name: "Sign Up" }).click();
    await signupRequest;
    await expect(page.getByRole("alert").first()).toHaveText(
      "An account with this email already exists.",
    );
  });

  test("login reports invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.context().addCookies([
      {
        name: "csrf_token",
        value: "e2e-token",
        url: "http://localhost:3000",
      },
    ]);
    await page.route("**/auth/session", async (route) => {
      await route.fulfill({ status: 401, body: "{}" });
    });
    await page.route("**/auth/login", async (route) => {
      await route.fulfill({ status: 401, body: "{}" });
    });

    await page.getByPlaceholder("Email").fill("unknown@example.com");
    await page.getByPlaceholder("Password").fill("wrong-password");
    await expect(page.getByPlaceholder("Email")).toHaveValue(
      "unknown@example.com",
    );
    await expect(page.getByPlaceholder("Password")).toHaveValue(
      "wrong-password",
    );
    await page.getByRole("button", { name: "Sign In" }).click();

    await expect(page.getByRole("alert").first()).toHaveText(
      "Unable to sign in. Check your email and password, or verify your account.",
    );
  });

  test("catalog search renders results and supports clearing", async ({
    page,
  }) => {
    await page.route(/\/api\/v1\/games/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            bgg_id: 13,
            primary_name: "Catan",
            year_published: 1995,
            thumbnail_url: null,
            average_rating: 7.1,
            bgg_rank: 1,
          },
        ]),
      });
    });

    await page.goto("/games/search");
    await page.getByPlaceholder("Search games...").fill("cat");
    await expect(page.getByRole("button", { name: "Search" })).toBeEnabled();
    await page.getByRole("button", { name: "Search" }).click();

    await expect(page.getByRole("heading", { name: "Catan" })).toBeVisible();
    await page.getByRole("button", { name: "Clear" }).click();
    await expect(
      page.getByText("Ready to find your next favorite game?"),
    ).toBeVisible();
  });

  test("library filtering shows an empty state for unmatched games", async ({
    page,
  }) => {
    await page.route(/\/api\/v1\/library\/(?:\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.goto("/library");
    const searchInput = page.getByPlaceholder("Search your collection...");
    await searchInput.fill("not a game");
    await expect(searchInput).toHaveValue("not a game");

    await expect(page.getByText("No games match your search.")).toBeVisible();
  });
});
