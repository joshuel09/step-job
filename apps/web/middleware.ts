import createMiddleware from "next-intl/middleware";
import { type NextRequest, NextResponse } from "next/server";

import { DEV_SESSION_COOKIE, devSessionEnabled, isUserId } from "./lib/dev-session";
import { defaultLocale, locales } from "./i18n";

// The browser's language only picks the starting point for someone who has not
// chosen yet; once a user sets their locale it is stored server-side and applies
// on every device (research.md R-003).
const intl = createMiddleware({
  locales,
  defaultLocale,
  localeDetection: true,
});

export default function middleware(request: NextRequest) {
  if (devSessionEnabled() && !isUserId(request.cookies.get(DEV_SESSION_COOKIE)?.value)) {
    // Issued by redirecting to the same address rather than passing straight
    // through: a cookie set on this response is not visible to the server
    // components rendering it, so the first page would load as signed out.
    const response = NextResponse.redirect(request.nextUrl);
    response.cookies.set(DEV_SESSION_COOKIE, crypto.randomUUID(), {
      path: "/",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 365,
    });
    return response;
  }
  return intl(request);
}

export const config = {
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
