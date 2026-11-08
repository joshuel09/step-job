import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import en from "../messages/en.json";

const readiness = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ api: { resumeReadiness: readiness } }));
vi.mock("next-intl/server", () => ({
  getTranslations: async () => (key: string) =>
    en.profile.resume[key as keyof typeof en.profile.resume],
}));

import { ResumeReadiness } from "../components/profile/resume-readiness";

const emptyReport = {
  can_generate: true,
  missing_required: [],
  needs_english: [],
  untranslated_names: [],
  stale_translations: [],
};
beforeEach(() => {
  readiness.mockReset();
});
const render = async () => renderToStaticMarkup(await ResumeReadiness({ locale: "en" }));

describe("resume readiness", () => {
  it("shows untranslated text and names, and retains stale approved words beside the current source", async () => {
    readiness.mockResolvedValue({
      ...emptyReport,
      needs_english: [
        {
          entry_type: "work_experience",
          entry_id: "role-1",
          field: "job_title",
          label: "Acme",
          source_text: "課長",
        },
      ],
      untranslated_names: [
        {
          entry_type: "certification",
          entry_id: "cert-1",
          field: "issuer",
          recorded_name: "認定機関",
        },
      ],
      stale_translations: [
        {
          id: "translation-1",
          source_text: "更新した原文",
          text: "Approved English",
          is_stale: true,
        },
      ],
    });
    const html = await render();
    for (const text of [
      "Acme",
      "課長",
      "認定機関",
      "更新した原文",
      "Approved English",
      en.profile.resume.staleNote,
    ])
      expect(html).toContain(text);
    expect(html).not.toContain(en.profile.resume.ready);
    expect(html).toContain('href="/en/profile"');
  });

  it("does not claim readiness when checking failed", async () => {
    readiness.mockRejectedValue(new Error("offline"));
    const html = await render();
    expect(html).toContain(en.profile.resume.unchecked);
    expect(html).not.toContain(en.profile.resume.ready);
  });

  it("names missing profile data instead of showing raw known field names", async () => {
    readiness.mockResolvedValue({
      ...emptyReport,
      can_generate: false,
      missing_required: ["identity", "experiences"],
    });
    const html = await render();
    expect(html).toContain(en.profile.resume.nameRequired);
    expect(html).toContain(en.profile.resume.experienceRequired);
    expect(html).not.toContain(en.profile.resume.ready);
  });

  it("reports a fully prepared profile", async () => {
    readiness.mockResolvedValue(emptyReport);
    expect(await render()).toContain(en.profile.resume.ready);
  });
});
