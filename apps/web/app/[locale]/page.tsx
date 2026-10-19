import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";

import { LocaleSwitcher } from "@/components/locale-switcher";
import { AVAILABLE, PLANNED, STEPS } from "@/lib/site";

/**
 * The first page anyone sees.
 *
 * It names only what the product does today. 職務経歴書 and the English resume
 * are specified and unbuilt, so they appear as work in progress rather than as
 * links — a landing page that offers a document the product cannot produce is
 * the same kind of untrue claim Principle IV forbids a generated document.
 */

export default async function Home({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  // Without this next-intl reads the request headers, which would force every
  // page to render dynamically. Server-first rendering is a constitution
  // requirement, so each page sets the locale explicitly.
  setRequestLocale(locale);
  const t = await getTranslations("home");
  const common = await getTranslations("common");

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-12 p-6">
      <header className="flex items-center justify-between gap-4">
        <span className="font-semibold">{common("appName")}</span>
        <div className="flex items-center gap-4">
          <LocaleSwitcher />
          <Link href={`/${locale}/profile`} className="text-sm underline">
            {t("nav")}
          </Link>
        </div>
      </header>

      <main className="flex flex-col gap-12">
        <section className="flex flex-col gap-4">
          <h1 className="text-3xl font-semibold tracking-tight">{t("headline")}</h1>
          <p className="max-w-xl text-base opacity-80">{t("lead")}</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <Link
              href={`/${locale}/profile`}
              className="rounded bg-neutral-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-neutral-900"
            >
              {t("start")}
            </Link>
            <Link
              href={`/${locale}/profile/documents/rirekisho`}
              className="rounded border border-neutral-300 px-4 py-2 text-sm dark:border-neutral-700"
            >
              {t("generate")}
            </Link>
          </div>
        </section>

        <section className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold">{t("howTitle")}</h2>
          <ol className="flex flex-col gap-4">
            {STEPS.map((step, index) => (
              <li key={step} className="flex gap-3">
                <span className="text-sm tabular-nums opacity-50">{index + 1}</span>
                <div>
                  <h3 className="text-sm font-medium">{t(`steps.${step}.title`)}</h3>
                  <p className="mt-1 text-sm opacity-70">{t(`steps.${step}.body`)}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold">{t("availableTitle")}</h2>
          <ul className="grid gap-3 sm:grid-cols-2">
            {AVAILABLE.map(({ key, href }) => (
              <li key={key}>
                <Link
                  href={`/${locale}/${href}`}
                  className="flex h-full flex-col gap-1 rounded border border-neutral-200 p-4 hover:border-neutral-400 dark:border-neutral-800 dark:hover:border-neutral-600"
                >
                  <span className="text-sm font-medium underline">
                    {t(`available.${key}.title`)}
                  </span>
                  <span className="text-sm opacity-70">{t(`available.${key}.body`)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">{t("plannedTitle")}</h2>
          <p className="text-sm opacity-70">{t("plannedBody")}</p>
          <ul className="flex flex-col gap-1">
            {PLANNED.map((item) => (
              <li key={item} className="text-sm opacity-70">
                {t(`planned.${item}`)}
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded border border-neutral-200 p-4 dark:border-neutral-800">
          <h2 className="text-sm font-medium">{t("truthTitle")}</h2>
          <p className="mt-1 text-sm opacity-70">{t("truthBody")}</p>
        </section>
      </main>
    </div>
  );
}
