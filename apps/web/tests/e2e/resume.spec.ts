import { expect, test } from "@playwright/test";

for (const locale of ["en", "ja"] as const) {
  test(`resume choices, download, metadata and missing-profile errors in ${locale}`, async ({
    page,
  }) => {
    const japanese = locale === "ja";
    await page.goto(`/${locale}/profile/documents/resume`);
    await expect(
      page.getByRole("heading", {
        name: japanese ? "英文レジュメ" : "English resume",
        exact: true,
      }),
    ).toBeVisible();
    const paper = page.getByLabel(japanese ? "用紙サイズ" : "Paper", { exact: true });
    await expect(paper).toHaveValue("letter");
    await paper.selectOption("a4");
    await page.getByLabel(japanese ? "スキルを含める" : "Include skills").uncheck();

    let attempt = 0;
    await page.route("**/api/v1/profile/documents/resume", async (route) => {
      expect(route.request().postDataJSON()).toEqual({ paper_size: "a4", include_skills: false });
      if (attempt++ === 0) {
        await route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({
            failures: [{ field: "experiences", reason: "Work experience is required" }],
          }),
        });
      } else {
        await route.fulfill({
          contentType: "application/pdf",
          body: "%PDF-test",
          headers: {
            "Content-Disposition": 'attachment; filename="english-resume.pdf"',
            "X-Document-Pages": "3",
            "X-Snapshot-Id": "snapshot-browser-123",
            "Access-Control-Expose-Headers": "Content-Disposition, X-Document-Pages, X-Snapshot-Id",
          },
        });
      }
    });
    const generate = page.getByRole("button", {
      name: japanese ? "作成する" : "Generate",
      exact: true,
    });
    await generate.click();
    await expect(page.getByRole("main").getByRole("alert")).toContainText(
      japanese ? "職歴を追加" : "Add work experience",
    );
    await generate.click();
    await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
    await expect(page.getByRole("status")).toContainText(japanese ? "3ページ" : "3 pages");
    await expect(page.getByRole("status")).toContainText("snapshot-browser-123");
    const preview = page.getByRole("link", {
      name: japanese ? "新しいタブでプレビュー" : "Open preview in a new tab",
    });
    await expect(preview).toHaveAttribute("href", /^blob:/);
    await expect(preview).toHaveAttribute("target", "_blank");
    const download = page.getByRole("link", {
      name: japanese ? "PDFをダウンロード" : "Download PDF",
    });
    const downloadEvent = page.waitForEvent("download");
    await download.click();
    expect((await downloadEvent).suggestedFilename()).toBe("english-resume.pdf");
    expect(await page.locator("body").innerText()).not.toMatch(/\b(common|profile)\.[a-zA-Z.]+\b/);
  });
}
