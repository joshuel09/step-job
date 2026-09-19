import { expect, test } from "@playwright/test";

/**
 * Quickstart Scenario 6 — the interface works fully in both languages.
 *
 * The part worth guarding is FR-023: switching the interface must not touch
 * what the user wrote. Translating someone's career entry because they changed
 * the menu language would be a data-integrity failure, not a display bug.
 */
test.describe("interface language", () => {
  test("defaults to English and offers both languages", async ({ page }) => {
    await page.goto("/en/profile");

    const switcher = page.getByLabel("Language");
    await expect(switcher).toBeVisible();
    await expect(switcher).toHaveValue("en");
  });

  test("switching to Japanese translates the interface", async ({ page }) => {
    await page.goto("/en/profile");
    await page.getByLabel("Language").selectOption("ja");

    await expect(page).toHaveURL(/\/ja\/profile/);
    await expect(page.getByRole("heading", { name: "職務プロフィール" })).toBeVisible();
  });

  test("switching the interface does not translate what the user typed", async ({ page }) => {
    await page.goto("/en/profile");

    const typed = "Built and maintained internal services.";
    await page.getByLabel("What you did").fill(typed);

    await page.getByLabel("Language").selectOption("ja");
    await expect(page).toHaveURL(/\/ja\/profile/);

    // The label is Japanese; the content the user wrote is untouched.
    await expect(page.getByLabel("業務内容")).toHaveValue(typed);
  });

  test("Japanese interface leaves no untranslated keys on screen", async ({ page }) => {
    await page.goto("/ja/profile");

    // A missing translation renders as its dotted key path.
    const body = await page.locator("body").innerText();
    expect(body).not.toMatch(/\b(common|profile)\.[a-zA-Z.]+\b/);
  });
});
