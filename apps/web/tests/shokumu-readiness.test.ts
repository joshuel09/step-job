import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import en from "../messages/en.json";
import ja from "../messages/ja.json";

const readiness = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({
  api: { shokumuReadiness: readiness },
  ApiError: class extends Error {
    status = 404;
  },
}));
vi.mock("next-intl/server", () => ({
  getTranslations: async () => (key: string) =>
    key.startsWith("fields.")
      ? en.profile.shokumu.fields[key.slice(7) as keyof typeof en.profile.shokumu.fields]
      : en.profile.shokumu[key as keyof typeof en.profile.shokumu],
}));
import { ShokumuReadiness, SHOKUMU_FIELDS } from "../components/profile/shokumu-readiness";
const empty = {
  can_generate: true,
  missing_required: [],
  missing_optional: [],
  unattached_achievements: [],
};
beforeEach(() => {
  readiness.mockReset();
});
const render = async () => renderToStaticMarkup(await ShokumuReadiness({ locale: "en" }));

describe("career history readiness", () => {
  it("distinguishes missing essentials, optional blanks and included unattached stories", async () => {
    readiness.mockResolvedValue({
      ...empty,
      can_generate: false,
      missing_required: ["identity", "experiences", "unknown"],
      missing_optional: ["skills"],
      unattached_achievements: [{ entry_id: "story-1", title: "My recorded achievement" }],
    });
    const html = await render();
    for (const value of [
      "Your name",
      "Work history",
      "Skills",
      "Other profile information",
      "My recorded achievement",
      en.profile.shokumu.unattachedNote,
    ])
      expect(html).toContain(value);
    expect(html).not.toContain(en.profile.shokumu.ready);
  });
  it("does not claim completeness when the check failed", async () => {
    readiness.mockRejectedValue(new Error("offline"));
    const html = await render();
    expect(html).toContain(en.profile.shokumu.unchecked);
    expect(html).not.toContain(en.profile.shokumu.ready);
  });
  it("shows the ready state", async () => {
    readiness.mockResolvedValue(empty);
    expect(await render()).toContain(en.profile.shokumu.ready);
  });
  it.each([en, ja])("has all computed field labels", (messages) => {
    const fields = messages.profile.shokumu.fields;
    for (const key of [...Object.values(SHOKUMU_FIELDS), "other"])
      expect(typeof fields[key as keyof typeof fields]).toBe("string");
  });
});
