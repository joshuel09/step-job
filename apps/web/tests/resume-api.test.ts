import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, ValidationError } from "../lib/api";

vi.mock("../lib/dev-session", () => ({
  currentUserId: async () => "3f2b8c1e-9a4d-4c7e-b2f1-0d6a5e8c9b7a",
  authorization: (id: string) => ({ Authorization: `Bearer ${id}` }),
}));

const fetchMock = vi.fn();
beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("resume generation", () => {
  it("sends the user's choices and preserves PDF metadata", async () => {
    fetchMock.mockResolvedValue(
      new Response("%PDF-test", {
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": 'attachment; filename="english-resume.pdf"',
          "X-Document-Pages": "3",
          "X-Snapshot-Id": "snapshot-123",
        },
      }),
    );
    const result = await api.generateResume({ paper_size: "a4", include_skills: false });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toMatch(/\/profile\/documents\/resume$/);
    expect(JSON.parse(init.body)).toEqual({ paper_size: "a4", include_skills: false });
    expect(init.headers.Authorization).toBe("Bearer 3f2b8c1e-9a4d-4c7e-b2f1-0d6a5e8c9b7a");
    expect(init.credentials).toBe("include");
    expect(await result.blob.text()).toBe("%PDF-test");
    expect(result).toMatchObject({
      filename: "english-resume.pdf",
      pages: 3,
      snapshotId: "snapshot-123",
    });
  });

  it.each(["resume", "rirekisho"] as const)(
    "uses the correct fallback filename for %s",
    async (kind) => {
      fetchMock.mockResolvedValue(new Response("%PDF-test"));
      const result =
        kind === "resume"
          ? await api.generateResume({ include_skills: true })
          : await api.generateRirekisho();
      expect(result.filename).toBe(`${kind}.pdf`);
    },
  );

  it("preserves the missing profile fields on 422", async () => {
    const failures = [{ field: "experiences", reason: "Add work experience" }];
    fetchMock.mockResolvedValue(Response.json({ failures }, { status: 422 }));
    const error = await api.generateResume({ include_skills: true }).catch((error) => error);
    expect(error).toBeInstanceOf(ValidationError);
    expect(error.failures).toEqual(failures);
  });

  it("reports a non-JSON failure instead of treating it as a PDF", async () => {
    fetchMock.mockResolvedValue(new Response("Unavailable", { status: 503 }));
    await expect(api.generateResume({ include_skills: true })).rejects.toBeInstanceOf(ApiError);
  });

  it("reads readiness without producing a document", async () => {
    const report = {
      can_generate: true,
      missing_required: [],
      needs_english: [],
      untranslated_names: [],
      stale_translations: [],
    };
    fetchMock.mockResolvedValue(Response.json(report));
    expect(await api.resumeReadiness()).toEqual(report);
    expect(fetchMock.mock.calls[0]![0]).toMatch(/\/resume\/readiness$/);
    expect(fetchMock.mock.calls[0]![1].method).toBeUndefined();
  });
});
