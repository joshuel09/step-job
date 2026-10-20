/**
 * A development-only session, standing in for sign-in until it is built.
 *
 * research.md R-006 puts authentication at the web layer, and that layer does
 * not exist yet. The API's local contract accepts a bare user UUID as the
 * bearer token (`_verify` in app/core/identity.py), so this gives each browser
 * a random UUID in a cookie and sends it with every call. Without it every
 * request is a 401 and the profile pages look finished but do nothing (#119).
 *
 * Off unless NEXT_PUBLIC_DEV_SESSION is "1". Anyone holding the cookie is that
 * user, which is fine on a developer's machine and nowhere else.
 */

export const DEV_SESSION_COOKIE = "stepjob_dev_user";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function devSessionEnabled(): boolean {
  return process.env.NEXT_PUBLIC_DEV_SESSION === "1";
}

/** A user id the API will accept; anything else is treated as no session. */
export function isUserId(value: string | undefined | null): value is string {
  return typeof value === "string" && UUID.test(value);
}

/** One cookie's value from a `Cookie` header or `document.cookie`. */
export function readCookie(header: string, name: string): string | undefined {
  for (const part of header.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return undefined;
}

/** The headers that identify the caller, or none if there is no session. */
export function authorization(userId: string | undefined): Record<string, string> {
  return isUserId(userId) ? { Authorization: `Bearer ${userId}` } : {};
}

/** The caller's user id, wherever the request is made from. */
export async function currentUserId(): Promise<string | undefined> {
  if (!devSessionEnabled()) return undefined;

  if (typeof document !== "undefined") {
    return readCookie(document.cookie, DEV_SESSION_COOKIE);
  }

  // A server component's fetch carries no browser cookies, so read the
  // incoming request's and forward the id ourselves.
  const { cookies } = await import("next/headers");
  return (await cookies()).get(DEV_SESSION_COOKIE)?.value;
}
