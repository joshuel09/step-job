import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

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
