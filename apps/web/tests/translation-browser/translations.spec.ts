import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";

/** Establish an isolated fixture owner for both server and browser API calls. */
async function signIn(page: Page, owner = randomUUID()) {
  await page
    .context()
    .addCookies([{ name: "stepjob_dev_user", value: owner, domain: "localhost", path: "/" }]);
}

for (const locale of ["en", "ja"] as const) {
  const ja = locale === "ja";
  test(`compare, explicitly approve exact English, and supply names in ${locale}`, async ({
    page,
  }) => {
    await signIn(page);
    const approvals: unknown[] = [];
    const patches: unknown[] = [];
    page.on("request", (request) => {
      if (request.method() === "PUT" && request.url().endsWith("/translations"))
        approvals.push(request.postDataJSON());
      if (request.method() === "PATCH") patches.push(request.postDataJSON());
    });
    await page.goto(`/${locale}/profile/translations`);
    const card = page.getByRole("article", { name: "株式会社サンプル" });
    const english = card.getByLabel(ja ? "承認する英語" : "English to approve");
    const approve = card.getByRole("button", {
      name: ja ? "英語を承認して保存" : "Approve and save English",
    });
    await expect(english).toHaveValue("");
    await expect(approve).toBeDisabled();
    await english.fill("  \n ");
    await expect(approve).toBeDisabled();
    await card.getByRole("button", { name: ja ? "英訳案を作成" : "Suggest English" }).click();
    await expect(english).toHaveValue("  \n ");
    await expect(approve).toBeDisabled();
    await card
      .getByRole("button", { name: ja ? "この翻訳案を使用" : "Use this suggestion", exact: true })
      .click();
    await expect(english).toHaveValue("Manager");
    await expect(card.getByText("課長", { exact: true }).first()).toBeVisible();
    expect(approvals).toEqual([]);
    const choice = card.getByLabel(ja ? "意味を選択" : "Choose a meaning");
    await expect(choice).toHaveValue("");
    await expect(approve).toBeDisabled();
    await choice.selectOption({ label: "Section Chief" });
    await expect(english).toHaveValue("Section Chief");
    await choice.selectOption("");
    await expect(approve).toBeDisabled();
    await choice.selectOption({ label: "Section Chief" });
    await english.fill("  Section Chief\n");
    await approve.click();
    await expect(page.getByRole("status")).toContainText(
      ja ? "プロフィールに保存" : "saved to your profile",
    );
    await expect(card).toHaveCount(0);
    expect(approvals).toEqual([
      {
        entry_type: "work_experience",
        entry_id: "11111111-1111-4111-8111-111111111111",
        field: "job_title",
        text: "  Section Chief\n",
      },
    ]);
    await page.reload();
    await expect(card).toHaveCount(0);

    const names = page.getByRole("region", {
      name: ja ? "正式な英語名称を入力" : "Supply official English names",
    });
    await expect(
      names.getByRole("button", { name: ja ? "英訳案を作成" : "Suggest English" }),
    ).toHaveCount(0);
    await names.getByLabel(ja ? "正式な英語名称" : "Official English name").fill("Sample Co.");
    await names.getByRole("button", { name: ja ? "英語名称を保存" : "Save English name" }).click();
    await expect(names).toHaveCount(0);
    expect(patches).toEqual([{ employer_name_english: "Sample Co." }]);
    expect(await page.locator("body").innerText()).not.toMatch(/\b(common|profile)\.[a-zA-Z.]+\b/);
  });

  test(`keep manual English on 503/502 and permit explicit manual approval in ${locale}`, async ({
    page,
  }) => {
    await signIn(page);
    await page.goto(`/${locale}/profile/translations`);
    const card = page.getByRole("article", { name: "株式会社サンプル" });
    const english = card.getByLabel(ja ? "承認する英語" : "English to approve");
    await english.fill("My own English");
    let status = 503;
    await page.route("**/translations/drafts", (route) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify({ code: "upstream" }),
      }),
    );
    const draft = card.getByRole("button", { name: ja ? "英訳案を作成" : "Suggest English" });
    await draft.click();
    await expect(card.getByRole("alert")).toContainText(ja ? "接続できません" : "unavailable");
    await expect(english).toHaveValue("My own English");
    status = 502;
    await draft.click();
    await expect(card.getByRole("alert")).toContainText(ja ? "使用できる翻訳案" : "unusable draft");
    await expect(english).toHaveValue("My own English");
    await card
      .getByRole("button", { name: ja ? "英語を承認して保存" : "Approve and save English" })
      .click();
    await expect(card).toHaveCount(0);
  });
}

test("stale English stays beside the current source and can be replaced without drafting", async ({
  page,
}) => {
  await signIn(page);
  await page.goto("/en/profile/translations");
  const stale = page.getByRole("region", { name: "Approved English to check" });
  await expect(stale.getByText("新しい名称", { exact: true })).toBeVisible();
  await expect(stale.getByLabel("English to approve")).toHaveValue("Old skill");
  await stale.getByLabel("English to approve").fill("New skill");
  await stale.getByRole("button", { name: "Approve and save English" }).click();
  await expect(stale).toHaveCount(0);
});

test("removing an old approval returns the field to the English worklist", async ({ page }) => {
  await signIn(page);
  await page.goto("/en/profile/translations");
  const stale = page.getByRole("region", { name: "Approved English to check" });
  await stale.getByRole("button", { name: "Remove approval and use the source" }).click();
  await expect(stale).toHaveCount(0);
  await expect(
    page
      .getByRole("region", { name: "Entries needing English" })
      .getByRole("article", { name: "新しい名称" }),
  ).toBeVisible();
});

test("a failed worklist read does not claim there is no work", async ({ page }) => {
  await signIn(page, "00000000-0000-4000-8000-000000000503");
  await page.goto("/en/profile/translations");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("could not load");
  await expect(page.getByText("No recorded resume fields are waiting for English.")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Refresh from profile" })).toBeEnabled();
});

test("an unambiguous draft can be approved and failed approval preserves edits", async ({
  page,
}) => {
  await signIn(page);
  await page.goto("/en/profile/translations");
  const stale = page.getByRole("region", { name: "Approved English to check" });
  await stale.getByRole("button", { name: "Suggest English" }).click();
  await expect(stale.getByLabel("English to approve")).toHaveValue("Old skill");
  await expect(stale.getByRole("button", { name: "Approve and save English" })).toBeDisabled();
  await stale.getByRole("button", { name: "Use this suggestion", exact: true }).click();
  await expect(stale.getByLabel("English to approve")).toHaveValue("New skill");
  await expect(stale.getByLabel("Choose a meaning")).toHaveCount(0);
  await stale.getByLabel("English to approve").fill("Corrected skill");
  await page.route("**/api/v1/profile/translations", (route) =>
    route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({ failures: [] }),
    }),
  );
  await stale.getByRole("button", { name: "Approve and save English" }).click();
  await expect(stale.getByRole("alert")).toContainText("could not be saved");
  await expect(stale.getByLabel("English to approve")).toHaveValue("Corrected skill");
});

test("a missing profile offers recording rather than an empty success", async ({ page }) => {
  await signIn(page, "00000000-0000-4000-8000-000000000404");
  await page.goto("/en/profile/translations");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("no profile");
  await expect(page.getByRole("article")).toHaveCount(0);
});

test("Japanese comparison fits a mobile viewport", async ({ page }, testInfo) => {
  await signIn(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/ja/profile/translations");
  await expect(page.getByRole("article", { name: "株式会社サンプル" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("translation-review-mobile.png"),
    fullPage: true,
  });
});

test("unknown name fields explain why they cannot be edited", async ({ page }) => {
  await signIn(page, "00000000-0000-4000-8000-000000000499");
  await page.goto("/en/profile/translations");
  const names = page.getByRole("region", { name: "Supply official English names" });
  await expect(names).toContainText("cannot be edited here yet");
  await expect(names.getByRole("textbox")).toHaveCount(0);
});

test("a failed post-save refresh does not contradict the confirmed save", async ({ page }) => {
  await signIn(page, "00000000-0000-4000-8000-000000000504");
  await page.goto("/en/profile/translations");
  const card = page.getByRole("article", { name: "株式会社サンプル" });
  await card.getByLabel("English to approve").fill("My approved English");
  await card.getByRole("button", { name: "Approve and save English" }).click();
  await expect(page.getByRole("status")).toContainText("was saved");
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "confirmed saves or removals are already stored",
  );
});

test("discarding a suggestion keeps the user's existing English", async ({ page }) => {
  await signIn(page);
  await page.goto("/en/profile/translations");
  const card = page.getByRole("article", { name: "株式会社サンプル" });
  await card.getByLabel("English to approve").fill("My own English");
  await card.getByRole("button", { name: "Suggest English", exact: true }).click();
  await expect(card.getByLabel("English to approve")).toHaveValue("My own English");
  await expect(card.getByRole("button", { name: "Approve and save English" })).toBeDisabled();
  await card.getByRole("button", { name: "Discard suggestion and use my wording" }).click();
  await expect(card.getByLabel("English to approve")).toHaveValue("My own English");
  await expect(card.getByRole("button", { name: "Approve and save English" })).toBeEnabled();
});
