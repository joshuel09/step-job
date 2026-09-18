import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";

export const locales = ["en", "ja"] as const;
export type Locale = (typeof locales)[number];

// English is the default for a new user (FR-021). A user's own choice is
// persisted by the API and wins over anything the browser reports (R-003).
export const defaultLocale: Locale = "en";

export default getRequestConfig(async ({ locale }) => {
  if (!locales.includes(locale as Locale)) notFound();
  return { messages: (await import(`./messages/${locale}.json`)).default };
});
