import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";

import { BrandMark } from "@/components/brand/footsteps";
import { GLYPHS } from "@/components/brand/icons";
import { Cat, Josh, Mich } from "@/components/brand/people";
import { DeskScene } from "@/components/brand/scene";
import { Wordmark } from "@/components/brand/wordmark";
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

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 border-b border-white/50 bg-white/60 backdrop-blur-xl dark:border-white/10 dark:bg-[#081726]/60">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-6 py-3">
          <Wordmark />
          <div className="flex items-center gap-4">
            <LocaleSwitcher />
            <Link
              href={`/${locale}/profile`}
              className="text-sm font-medium text-brand-700 underline-offset-4 hover:underline dark:text-brand-200"
            >
              {t("nav")}
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-4xl flex-col gap-16 px-6 pb-20 pt-14">
        <section className="grid animate-rise items-center gap-10 lg:grid-cols-[1fr_auto]">
          <div className="flex flex-col items-start gap-5">
            <span className="inline-flex items-center gap-2 rounded-full border border-brand-200/70 bg-white/60 px-3 py-1 text-xs font-medium uppercase tracking-[0.14em] text-brand-700 backdrop-blur dark:border-brand-300/20 dark:bg-white/5 dark:text-brand-200">
              {t("brandline")}
            </span>
            <h1 className="max-w-2xl text-pretty text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
              {t("headline")}
            </h1>
            <p className="max-w-xl text-base leading-relaxed text-ink-soft dark:text-brand-100/80">
              {t("lead")}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <Link href={`/${locale}/profile`} className="btn-primary">
                {t("start")}
              </Link>
              <Link href={`/${locale}/profile/documents/rirekisho`} className="btn-secondary">
                {t("generate")}
              </Link>
            </div>
          </div>
          <DeskScene className="hidden w-[22rem] drop-shadow-[0_24px_48px_rgba(3,105,161,0.18)] lg:block" />
        </section>

        <section className="flex flex-col gap-5">
          <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-faint">
            {t("howTitle")}
          </h2>
          <ol className="grid gap-4 sm:grid-cols-3">
            {STEPS.map((step, index) => (
              <li key={step} className="glass flex flex-col gap-2 rounded-card p-5">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-xs font-semibold tabular-nums text-white">
                  {index + 1}
                </span>
                <h3 className="text-sm font-semibold">{t(`steps.${step}.title`)}</h3>
                <p className="text-sm leading-relaxed text-ink-soft dark:text-brand-100/75">
                  {t(`steps.${step}.body`)}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <section className="flex flex-col gap-5">
          <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-faint">
            {t("availableTitle")}
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2">
            {AVAILABLE.map(({ key, href }) => {
              const Glyph = GLYPHS[key];
              return (
                <li key={key}>
                  <Link
                    href={`/${locale}/${href}`}
                    className="glass group flex h-full items-start gap-4 rounded-card p-5 transition duration-300 hover:-translate-y-0.5 hover:shadow-lift"
                  >
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-100 to-brand-200 text-brand-700 dark:from-brand-400/20 dark:to-brand-600/20 dark:text-brand-200">
                      <Glyph className="h-5 w-5" />
                    </span>
                    <span className="flex flex-col gap-1">
                      <span className="text-sm font-semibold">{t(`available.${key}.title`)}</span>
                      <span className="text-sm leading-relaxed text-ink-soft dark:text-brand-100/75">
                        {t(`available.${key}.body`)}
                      </span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="flex flex-col gap-4">
          <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-faint">
            {t("plannedTitle")}
          </h2>
          <div className="rounded-card border border-dashed border-brand-300/60 p-5 dark:border-brand-300/25">
            <p className="text-sm text-ink-soft dark:text-brand-100/75">{t("plannedBody")}</p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {PLANNED.map((item) => (
                <li
                  key={item}
                  className="rounded-full bg-white/60 px-3 py-1 text-sm text-ink-soft dark:bg-white/5 dark:text-brand-100/75"
                >
                  {t(`planned.${item}`)}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="glass flex flex-col gap-2 rounded-card p-6">
          <h2 className="text-sm font-semibold">{t("truthTitle")}</h2>
          <p className="max-w-2xl text-sm leading-relaxed text-ink-soft dark:text-brand-100/75">
            {t("truthBody")}
          </p>
        </section>

        <section className="flex flex-col gap-5">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-faint">
              {t("makersTitle")}
            </h2>
            {/* The cat had a line in the 2018 About screen. It keeps it. */}
            <span className="flex items-center gap-2">
              <span className="rounded-full bg-white/70 px-3 py-1 text-xs text-ink-soft dark:bg-white/10 dark:text-brand-100/75">
                {t("makers.cat")}
              </span>
              <Cat className="h-7 w-9" />
            </span>
          </div>
          <ul className="grid gap-4 sm:grid-cols-2">
            {[
              { key: "josh", Portrait: Josh },
              { key: "mich", Portrait: Mich },
            ].map(({ key, Portrait }) => (
              <li key={key} className="glass flex items-center gap-4 rounded-card p-5">
                <Portrait className="h-14 w-14 shrink-0" />
                <div className="flex flex-col">
                  <span className="text-sm font-semibold">{t(`makers.${key}.name`)}</span>
                  <span className="text-sm text-ink-soft dark:text-brand-100/75">
                    {t(`makers.${key}.role`)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <footer className="flex items-center gap-3 text-xs text-ink-faint">
          <BrandMark className="h-5 w-5" gradientId="sj-footer" />
          <span>{t("since")}</span>
        </footer>
      </main>
    </div>
  );
}
