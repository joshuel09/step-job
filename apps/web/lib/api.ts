import type { Components002, components } from "@step-job/api-client";

type Schemas = components["schemas"];
type ImportSchemas = Components002["schemas"];

export type Profile = Schemas["Profile"];
export type Identity = Schemas["Identity"];
export type JapanProfile = Schemas["JapanProfile"];
export type WorkExperience = Schemas["WorkExperience"];
export type Education = Schemas["Education"];
export type Certification = Schemas["Certification"];
export type Skill = Schemas["Skill"];
export type Language = Schemas["Language"];
export type CareerPreference = Schemas["CareerPreference"];
export type CareerStory = Schemas["CareerStory"];
export type ProposedEntry = Schemas["ProposedEntry"];
export type CareerImport = ImportSchemas["ImportDetail"];
export type Locale = Schemas["Locale"];

/**
 * A validation rejection, carrying the field the API objected to and why.
 * FR-014 requires the interface show that reason rather than a generic failure,
 * so the shape is preserved all the way to the form field.
 */
export class ValidationError extends Error {
  readonly failures: { field: string; reason: string }[];

  constructor(failures: { field: string; reason: string }[], message = "Validation failed") {
    super(message);
    this.name = "ValidationError";
    this.failures = failures;
  }
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    credentials: "include",
    // Never cached: a profile page rendered from a build-time snapshot would
    // show one user's data, or an empty profile, to everyone.
    cache: "no-store",
  });

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 422 && body?.failures) {
      throw new ValidationError(body.failures, body.message);
    }
    throw new ApiError(response.status, body?.code ?? "error", body?.message ?? response.statusText);
  }

  return body as T;
}

export const api = {
  getProfile: () => request<Profile>("/profile"),
  createProfile: () => request<Profile>("/profile", { method: "POST" }),
  setLocale: (interface_locale: Locale) =>
    request<Profile>("/profile", {
      method: "PATCH",
      body: JSON.stringify({ interface_locale }),
    }),
  completeness: () =>
    request<Record<string, { complete: boolean; entry_count: number }>>("/profile/completeness"),

  putIdentity: (body: Identity) =>
    request<Identity>("/profile/identity", { method: "PUT", body: JSON.stringify(body) }),
  putJapan: (body: JapanProfile) =>
    request<JapanProfile>("/profile/japan", { method: "PUT", body: JSON.stringify(body) }),
  putPreferences: (body: CareerPreference) =>
    request<CareerPreference>("/profile/preferences", {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  createEntry: <T>(section: string, body: unknown) =>
    request<T>(`/profile/${section}`, { method: "POST", body: JSON.stringify(body) }),
  updateEntry: <T>(section: string, id: string, body: unknown) =>
    request<T>(`/profile/${section}/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteEntry: (section: string, id: string, confirm = false) =>
    request<void>(`/profile/${section}/${id}${confirm ? "?confirm=true" : ""}`, {
      method: "DELETE",
    }),

  listStories: (q?: string) =>
    request<CareerStory[]>(`/profile/stories${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  createStory: (body: unknown) =>
    request<CareerStory>("/profile/stories", { method: "POST", body: JSON.stringify(body) }),
  updateStory: (id: string, body: unknown) =>
    request<CareerStory>(`/profile/stories/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteStory: (id: string) => request<void>(`/profile/stories/${id}`, { method: "DELETE" }),

  listProposals: (status = "pending") =>
    request<ProposedEntry[]>(`/profile/proposals?status=${status}`),
  acceptProposal: (id: string, payload?: Record<string, unknown>) =>
    request<{ proposal_id: string; created_entry_id: string; entry_type: string }>(
      `/profile/proposals/${id}/accept`,
      { method: "POST", body: JSON.stringify({ payload: payload ?? null }) },
    ),
  rejectProposal: (id: string) =>
    request<void>(`/profile/proposals/${id}/reject`, { method: "POST" }),
  mergeProposal: (id: string, target_entry_id: string, payload?: Record<string, unknown>) =>
    request<WorkExperience>(`/profile/proposals/${id}/merge`, {
      method: "POST",
      body: JSON.stringify({ target_entry_id, payload: payload ?? null }),
    }),

  listImports: () => request<CareerImport[]>("/profile/imports"),
  getImport: (id: string) => request<CareerImport>(`/profile/imports/${id}`),
  importText: (text: string) =>
    request<CareerImport>("/profile/imports", { method: "POST", body: JSON.stringify({ text }) }),
  cancelImport: (id: string) =>
    request<CareerImport>(`/profile/imports/${id}/cancel`, { method: "POST" }),

  deleteProfile: () =>
    request<{ erased_immediately: string[]; recoverable_until: string }>("/profile", {
      method: "DELETE",
    }),
  restoreProfile: () => request<Profile>("/profile/restore", { method: "POST" }),
};
