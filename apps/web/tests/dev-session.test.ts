import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEV_SESSION_COOKIE,
  authorization,
  currentUserId,
  isUserId,
  readCookie,
} from "../lib/dev-session";

/**
 * #119: with no session, every API call is a 401 and the profile pages load
 * empty without saying why. These hold the development session to what the
 * API's local contract accepts, and to staying off unless asked for.
 */

const ID = "3f2b8c1e-9a4d-4c7e-b2f1-0d6a5e8c9b7a";

const cookies = vi.hoisted(() => ({ value: undefined as string | undefined }));
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) =>
      name === "stepjob_dev_user" && cookies.value ? { value: cookies.value } : undefined,
  }),
}));

beforeEach(() => vi.stubEnv("NEXT_PUBLIC_DEV_SESSION", "1"));
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  cookies.value = undefined;
});

describe("the bearer header", () => {
  it("carries the user id the way the API reads it", () => {
    expect(authorization(ID)).toEqual({ Authorization: `Bearer ${ID}` });
  });

  it("is left off rather than sent with something the API would refuse", () => {
    expect(authorization(undefined)).toEqual({});
    expect(authorization("")).toEqual({});
    expect(authorization("not-a-uuid")).toEqual({});
    expect(authorization(`${ID}x`)).toEqual({});
  });

  it("accepts only a UUID", () => {
    expect(isUserId(ID)).toBe(true);
    expect(isUserId(ID.toUpperCase())).toBe(true);
    expect(isUserId(" " + ID)).toBe(false);
  });
});

describe("reading the cookie", () => {
  it("finds it among others", () => {
    expect(readCookie(`NEXT_LOCALE=ja; ${DEV_SESSION_COOKIE}=${ID}; theme=dark`, DEV_SESSION_COOKIE)).toBe(ID);
  });

  it("does not match a cookie whose name only ends the same way", () => {
    expect(readCookie(`old_${DEV_SESSION_COOKIE}=${ID}`, DEV_SESSION_COOKIE)).toBeUndefined();
  });

  it("is absent from an empty header", () => {
    expect(readCookie("", DEV_SESSION_COOKIE)).toBeUndefined();
  });
});

describe("whose session a request carries", () => {
  it("is the incoming request's on the server", async () => {
    cookies.value = ID;
    expect(await currentUserId()).toBe(ID);
  });

  it("is the browser's in the browser", async () => {
    vi.stubGlobal("document", { cookie: `${DEV_SESSION_COOKIE}=${ID}` });
    expect(await currentUserId()).toBe(ID);
  });

  it("is nobody's unless the development session is switched on", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEV_SESSION", "");
    cookies.value = ID;
    expect(await currentUserId()).toBeUndefined();
  });
});

describe("every API call", () => {
  it("sends the session", async () => {
    cookies.value = ID;
    const fetch = vi.fn(async () => new Response(JSON.stringify({}), { status: 200 }));
    vi.stubGlobal("fetch", fetch);
    const { api } = await import("../lib/api");

    await api.getProfile();
    await api.generateRirekisho().catch(() => undefined);
    await api.uploadImport(new File(["x"], "cv.pdf"));

    expect(fetch).toHaveBeenCalledTimes(3);
    for (const [, init] of fetch.mock.calls as unknown as [string, RequestInit][]) {
      expect((init.headers as Record<string, string>).Authorization).toBe(`Bearer ${ID}`);
    }
  });
});

describe("issuing the session", () => {
  const visit = async (cookie?: string) => {
    const { default: middleware } = await import("../middleware");
    const headers = cookie ? { cookie } : undefined;
    return middleware(new NextRequest("http://localhost:3000/en/profile", { headers }));
  };

  it("gives a new browser an id, then sends it back to the same page", async () => {
    const response = await visit();

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/en/profile");
    expect(isUserId(response.cookies.get(DEV_SESSION_COOKIE)?.value)).toBe(true);
  });

  it("leaves a browser that already has one alone", async () => {
    const response = await visit(`${DEV_SESSION_COOKIE}=${ID}`);

    expect(response.cookies.get(DEV_SESSION_COOKIE)).toBeUndefined();
    expect(response.status).not.toBe(307);
  });

  it("replaces a cookie the API would refuse", async () => {
    const response = await visit(`${DEV_SESSION_COOKIE}=garbage`);
    expect(isUserId(response.cookies.get(DEV_SESSION_COOKIE)?.value)).toBe(true);
  });

  it("issues nothing when switched off", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEV_SESSION", "");
    const response = await visit();
    expect(response.cookies.get(DEV_SESSION_COOKIE)).toBeUndefined();
  });
});
