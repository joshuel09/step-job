import { getTranslations, setRequestLocale } from "next-intl/server";

export default async function Home({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  // Without this next-intl reads the request headers, which would force every
  // page to render dynamically. Server-first rendering is a constitution
  // requirement, so each page sets the locale explicitly.
  setRequestLocale(locale);
  const t = await getTranslations("common");

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">{t("appName")}</h1>
      <p className="mt-2 text-sm opacity-80">{t("tagline")}</p>
    </main>
  );
}
