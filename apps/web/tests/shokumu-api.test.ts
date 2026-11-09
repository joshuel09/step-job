import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, ValidationError } from "../lib/api";

vi.mock("../lib/dev-session", () => ({
  currentUserId: async () => "owner",
  authorization: () => ({ Authorization: "Bearer owner" }),
}));
const fetchMock = vi.fn();
beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("career history document client", () => {
  it("sends all choices with authentication and preserves PDF metadata", async () => {
    fetchMock.mockResolvedValue(
      new Response("%PDF-test", {
        headers: {
          "Content-Disposition": 'attachment; filename="career-history.pdf"',
          "X-Document-Pages": "4",
          "X-Snapshot-Id": "snapshot-004",
        },
      }),
    );
    const options = {
      arrangement: "chronological" as const,
      date_convention: "wareki" as const,
      paper_size: "b5" as const,
    };
    const result = await api.generateShokumuKeirekisho(options);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toMatch(/\/profile\/documents\/shokumu-keirekisho$/);
    expect(init).toMatchObject({
      method: "POST",
      credentials: "include",
      headers: { Authorization: "Bearer owner" },
    });
    expect(JSON.parse(init.body)).toEqual(options);
    expect(result).toMatchObject({
      filename: "career-history.pdf",
      pages: 4,
      snapshotId: "snapshot-004",
    });
    expect(await result.blob.text()).toBe("%PDF-test");
  });
  it("keeps missing profile fields on a refusal", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ failures: [{ field: "experiences", reason: "required" }] }, { status: 422 }),
    );
    const error = await api.generateShokumuKeirekisho({}).catch((error) => error);
    expect(error).toBeInstanceOf(ValidationError);
    expect(error.failures[0].field).toBe("experiences");
  });
  it("does not treat a missing profile as a PDF", async () => {
    fetchMock.mockResolvedValue(Response.json({ code: "not_found" }, { status: 404 }));
    await expect(api.generateShokumuKeirekisho({})).rejects.toBeInstanceOf(ApiError);
  });
  it("checks readiness without generating a document", async () => {
    const report = {
      can_generate: true,
      missing_required: [],
      missing_optional: ["skills"],
      unattached_achievements: [],
    };
    fetchMock.mockResolvedValue(Response.json(report));
    expect(await api.shokumuReadiness()).toEqual(report);
    expect(fetchMock.mock.calls[0]![0]).toMatch(/shokumu-keirekisho\/readiness$/);
    expect(fetchMock.mock.calls[0]![1].method).toBeUndefined();
  });
});
