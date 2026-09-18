import createMiddleware from "next-intl/middleware";

import { defaultLocale, locales } from "./i18n";

// The browser's language only picks the starting point for someone who has not
// chosen yet; once a user sets their locale it is stored server-side and applies
// on every device (research.md R-003).
export default createMiddleware({
  locales,
  defaultLocale,
  localeDetection: true,
});

export const config = {
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
