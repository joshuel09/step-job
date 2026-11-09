import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page, owner = randomUUID()) {
  await page
    .context()
    .addCookies([{ name: "stepjob_dev_user", value: owner, domain: "localhost", path: "/" }]);
}
for (const locale of ["en", "ja"] as const) {
  const ja = locale === "ja";
  test(`reach and generate career history in ${locale}`, async ({ page }) => {
    await signIn(page);
    await page.goto(`/${locale}/profile`);
    await page.getByRole("link", { name: "職務経歴書", exact: true }).first().click();
    await expect(page).toHaveURL(/documents\/shokumu-keirekisho$/);
    const main = page.getByRole("main");
    const order = page.getByLabel(ja ? "職歴の順序" : "Work history order");
    const dates = page.getByLabel(ja ? "日付の表記" : "Dates", { exact: true });
    const paper = page.getByLabel(ja ? "用紙サイズ" : "Paper", { exact: true });
    await expect(order).toHaveValue("reverse_chronological");
    await expect(dates).toHaveValue("seireki");
    await expect(paper).toHaveValue("a4");
    const requests: unknown[] = [];
    page.on("request", (request) => {
      if (request.method() === "POST" && request.url().endsWith("/shokumu-keirekisho"))
        requests.push(request.postDataJSON());
    });
    const generate = page.getByRole("button", { name: ja ? "作成する" : "Generate", exact: true });
    await generate.click();
    await expect(page.getByRole("status")).toContainText(ja ? "4ページ" : "4 pages");
    expect(requests[0]).toEqual({
      arrangement: "reverse_chronological",
      date_convention: "seireki",
      paper_size: "a4",
    });
    await order.selectOption("chronological");
    await dates.selectOption("wareki");
    await paper.selectOption("b5");
    await generate.click();
    await expect(page.getByRole("status")).toContainText("snapshot-004-full-reference");
    expect(requests[1]).toEqual({
      arrangement: "chronological",
      date_convention: "wareki",
      paper_size: "b5",
    });
    await expect(
      page.getByRole("link", { name: ja ? "新しいタブでプレビュー" : "Open preview in a new tab" }),
    ).toHaveAttribute("href", /^blob:/);
    const downloaded = page.waitForEvent("download");
    await page.getByRole("link", { name: ja ? "PDFをダウンロード" : "Download PDF" }).click();
    expect((await downloaded).suggestedFilename()).toBe("shokumu-keirekisho.pdf");
    expect(await main.innerText()).not.toMatch(/\b(common|profile)\.[a-zA-Z.]+\b/);
    await page.goto(`/${locale}`);
    await expect(
      page.getByRole("main").locator(`a[href="/${locale}/profile/documents/shokumu-keirekisho"]`),
    ).toBeVisible();
  });

  test(`show generation failures in ${locale}`, async ({ page }) => {
    await signIn(page);
    await page.goto(`/${locale}/profile/documents/shokumu-keirekisho`);
    let attempt = 0;
    await page.route("**/api/v1/profile/documents/shokumu-keirekisho", (route) => {
      attempt++;
      return route.fulfill({
        status: attempt === 4 ? 404 : 422,
        contentType: "application/json",
        body: JSON.stringify({
          failures:
            attempt === 1
              ? [
                  { field: "identity", reason: "private server detail" },
                  { field: "experiences", reason: "private server detail" },
                ]
              : attempt === 2
                ? [{ field: "paper_size", reason: "private server detail" }]
                : [],
        }),
      });
    });
    const generate = page.getByRole("button", { name: ja ? "作成する" : "Generate", exact: true });
    const alerts = page.getByRole("main").getByRole("alert");
    await generate.click();
    await expect(alerts).toHaveCount(2);
    await expect(alerts.first()).toContainText(ja ? "氏名" : "name");
    await expect(alerts.last()).toContainText(ja ? "職歴" : "work experience");
    await expect(alerts.first()).toContainText(
      ja ? "書類は作成されていません" : "No document was generated",
    );
    await generate.click();
    await expect(alerts).toContainText(ja ? "選択肢" : "listed options");
    await generate.click();
    await expect(alerts).toContainText(ja ? "エラー" : "Something went wrong");
    await generate.click();
    await expect(alerts).toContainText(ja ? "プロフィールがありません" : "No profile is available");
    await expect(page.getByRole("main")).not.toContainText("private server detail");
    await expect(page.getByRole("status")).toHaveCount(0);
  });
}

test("Japanese career history page fits mobile", async ({ page }, testInfo) => {
  await signIn(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/ja/profile/documents/shokumu-keirekisho");
  await expect(page.getByRole("heading", { name: "職務経歴書", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("shokumu-mobile.png"), fullPage: true });
});
