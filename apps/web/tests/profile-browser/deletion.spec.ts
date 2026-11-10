import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page, owner = randomUUID()) {
  await page
    .context()
    .addCookies([{ name: "stepjob_dev_user", value: owner, domain: "localhost", path: "/" }]);
}

async function mockDelete(
  page: Page,
  recoverableUntil = new Date(Date.now() + 30 * 86400000).toISOString(),
) {
  await page.route("**/api/v1/profile", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        erased_immediately: ["nationality", "visa_type"],
        recoverable_until: recoverableUntil,
      }),
    }),
  );
}

async function beginDelete(page: Page, locale: "en" | "ja" = "en") {
  await page.goto(`/${locale}/profile/settings`);
  await page
    .getByRole("button", { name: locale === "en" ? "Delete my profile" : "プロフィールを削除" })
    .click();
  const response = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/profile") && response.request().method() === "DELETE",
  );
  await page
    .getByRole("button", { name: locale === "en" ? "Yes, delete my profile" : "削除する" })
    .click();
  await response;
}

test("a restore reminder survives reload, stays with its account and clears after restore", async ({
  page,
}) => {
  const owner = randomUUID();
  await page
    .context()
    .addCookies([{ name: "stepjob_dev_user", value: owner, domain: "localhost", path: "/" }]);
  let restores = 0;
  await page.route("**/api/v1/profile", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        erased_immediately: ["nationality", "visa_type"],
        recoverable_until: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      }),
    }),
  );
  await page.route("**/api/v1/profile/restore", (route) => {
    restores++;
    return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  await page.goto("/en/profile/settings");
  await page.getByRole("button", { name: "Delete my profile" }).click();
  await page.getByRole("button", { name: "Yes, delete my profile" }).click();
  const restore = page.getByRole("button", { name: "Restore my profile" });
  await expect(restore).toBeVisible();
  await expect(
    page.getByText(/For privacy, this reminder stays in this browser and account/),
  ).toBeVisible();
  const savedReceipt = await page.evaluate(() =>
    Object.entries(localStorage).filter(([key]) => key.startsWith("step-job:profile-deletion:")),
  );
  expect(savedReceipt).toHaveLength(1);
  expect(JSON.stringify(savedReceipt)).not.toContain(owner);

  await page.reload();
  await expect(restore).toBeVisible();

  await page
    .context()
    .addCookies([
      { name: "stepjob_dev_user", value: randomUUID(), domain: "localhost", path: "/" },
    ]);
  await page.reload();
  await expect(page.getByRole("button", { name: "Delete my profile" })).toBeVisible();
  await expect(restore).toHaveCount(0);

  await page
    .context()
    .addCookies([{ name: "stepjob_dev_user", value: owner, domain: "localhost", path: "/" }]);
  await page.reload();
  await expect(restore).toBeVisible();
  await restore.click();
  await expect(page.getByRole("button", { name: "Delete my profile" })).toBeVisible();
  expect(restores).toBe(1);
  await page.reload();
  await expect(page.getByRole("button", { name: "Delete my profile" })).toBeVisible();
  await expect(restore).toHaveCount(0);
});

test("an expired restore reminder is removed on reload", async ({ page }) => {
  await page
    .context()
    .addCookies([
      { name: "stepjob_dev_user", value: randomUUID(), domain: "localhost", path: "/" },
    ]);
  await page.route("**/api/v1/profile", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        erased_immediately: ["nationality", "visa_type"],
        recoverable_until: "2020-01-01T00:00:00.000Z",
      }),
    }),
  );
  await page.goto("/en/profile/settings");
  await page.getByRole("button", { name: "Delete my profile" }).click();
  await page.getByRole("button", { name: "Yes, delete my profile" }).click();
  const restore = page.getByRole("button", { name: "Restore my profile" });
  await expect(restore).toBeVisible();
  await page.reload();
  await expect(restore).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Delete my profile" })).toBeVisible();
  expect(
    await page.evaluate(() =>
      Object.keys(localStorage).filter((key) => key.startsWith("step-job:profile-deletion:")),
    ),
  ).toEqual([]);
});

test("a malformed receipt is removed instead of shown", async ({ page }) => {
  await signIn(page);
  await mockDelete(page);
  await beginDelete(page);
  await page.evaluate(() => {
    const key = Object.keys(localStorage).find((name) =>
      name.startsWith("step-job:profile-deletion:"),
    );
    if (!key) throw new Error("receipt key missing");
    localStorage.setItem(
      key,
      JSON.stringify({ erased_immediately: [7], recoverable_until: "2099-01-01T00:00:00Z" }),
    );
  });
  await page.reload();
  await expect(page.getByRole("button", { name: "Restore my profile" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Delete my profile" })).toBeVisible();
});

test("unavailable browser storage explains why the reminder cannot load in Japanese", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Storage.prototype.getItem = function (key) {
      if (key.startsWith("step-job:profile-deletion:"))
        throw new DOMException("blocked", "SecurityError");
      return null;
    };
  });
  await page.goto("/ja/profile/settings");
  await expect(page.getByText(/このアカウントの復元情報を読み込めませんでした/)).toBeVisible();
  await expect(page.getByRole("main")).not.toContainText("Browser storage is unavailable");
});

test("failed deletion tells the user that no reminder was saved", async ({ page }) => {
  await signIn(page);
  await page.route("**/api/v1/profile", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ code: "private server detail" }),
    }),
  );
  await page.goto("/en/profile/settings");
  await page.getByRole("button", { name: "Delete my profile" }).click();
  await page.getByRole("button", { name: "Yes, delete my profile" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "could not confirm profile deletion",
  );
  await expect(page.getByRole("button", { name: "Restore my profile" })).toHaveCount(0);
  await expect(page.getByRole("main")).not.toContainText("private server detail");
});

test("storage write failure says deletion succeeded and keeps the current restore action", async ({
  page,
}) => {
  await signIn(page);
  await page.addInitScript(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key, value) {
      if (key.startsWith("step-job:profile-deletion:"))
        throw new DOMException("blocked", "SecurityError");
      return original.call(this, key, value);
    };
  });
  await mockDelete(page);
  await beginDelete(page, "ja");
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "プロフィールは削除されました",
  );
  await expect(page.getByRole("main").getByRole("alert")).toContainText("保存できませんでした");
  await expect(page.getByRole("button", { name: "プロフィールを復元" })).toBeVisible();
  await expect(page.getByRole("main")).not.toContainText("browser could not save");
});

test("failed restore keeps the receipt so the user can retry", async ({ page }) => {
  await signIn(page);
  await mockDelete(page);
  await page.route("**/api/v1/profile/restore", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ code: "private server detail" }),
    }),
  );
  await beginDelete(page);
  const restore = page.getByRole("button", { name: "Restore my profile" });
  await restore.click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "could not restore your profile",
  );
  await expect(restore).toBeEnabled();
  await expect(page.getByRole("main")).not.toContainText("private server detail");
});

test("failed reminder cleanup says the profile was restored", async ({ page }) => {
  await signIn(page);
  await page.addInitScript(() => {
    const original = Storage.prototype.removeItem;
    Storage.prototype.removeItem = function (key) {
      if (key.startsWith("step-job:profile-deletion:"))
        throw new DOMException("blocked", "SecurityError");
      return original.call(this, key);
    };
  });
  await mockDelete(page);
  await page.route("**/api/v1/profile/restore", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
  );
  await beginDelete(page);
  await page.getByRole("button", { name: "Restore my profile" }).click();
  await expect(page.getByRole("button", { name: "Delete my profile" })).toBeVisible();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Your profile was restored",
  );
});
