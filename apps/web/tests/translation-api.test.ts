import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, ValidationError } from "../lib/api";

vi.mock("../lib/dev-session", () => ({
  currentUserId: async () => "3f2b8c1e-9a4d-4c7e-b2f1-0d6a5e8c9b7a",
  authorization: (id: string) => ({ Authorization: `Bearer ${id}` }),
}));

const fetchMock = vi.fn();
const subject = { entry_type: "work_experience" as const, entry_id: "role-1", field: "job_title" };
beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("translation proposals and approvals", () => {
  it("requests a draft without submitting an approval", async () => {
    const draft = { ...subject, source_text: "課長", text: "Manager", alternatives: [] };
    fetchMock.mockResolvedValue(Response.json(draft));
    expect(await api.draftTranslation(subject)).toEqual(draft);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toMatch(/\/profile\/translations\/drafts$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual(subject);
    expect(init.headers.Authorization).toMatch(/^Bearer /);
  });

  it("sends exactly the English the user approved, including spacing", async () => {
    fetchMock.mockResolvedValue(Response.json({ id: "approval-1" }));
    await api.approveTranslation({ ...subject, text: "  Section Chief\n" });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toMatch(/\/profile\/translations$/);
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body).text).toBe("  Section Chief\n");
  });

  it.each([502, 503])("keeps the %s draft failure distinguishable", async (status) => {
    fetchMock.mockResolvedValue(Response.json({ code: "upstream" }, { status }));
    const error = await api.draftTranslation(subject).catch((error) => error);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(status);
  });

  it("preserves validation failures when approval is refused", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ failures: [{ field: "text", reason: "blank" }] }, { status: 422 }),
    );
    await expect(api.approveTranslation({ ...subject, text: " " })).rejects.toBeInstanceOf(
      ValidationError,
    );
  });

  it("deletes the selected stored version", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await api.deleteTranslation("approval-1");
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toMatch(/\/profile\/translations\/approval-1$/);
    expect(init.method).toBe("DELETE");
  });
});
