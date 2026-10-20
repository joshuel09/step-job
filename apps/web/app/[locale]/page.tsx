import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";
import type { ReactNode } from "react";

import { BrandMark } from "@/components/brand/footsteps";
import { GLYPHS } from "@/components/brand/icons";
import { Cat, Josh, Mich } from "@/components/brand/people";
import { DeskScene } from "@/components/brand/scene";
import { Wordmark } from "@/components/brand/wordmark";
import { World } from "@/components/landing/world";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { AVAILABLE, PLANNED, PROFILE_LINKS, STEPS } from "@/lib/site";

/**
 * The first page anyone sees.
 *
 * Built as a place rather than a brochure: the drawing runs the full width
 * at the top, and the sections under it are signs around the same garden —
 * paper, line and one warm orange, so the page and the illustration are
 * plainly the same thing.
 *
 * It names only what the product does today. 職務経歴書 and the English
 * resume are specified and unbuilt, so they appear as work in progress
 * rather than as links — a landing page that offers a document the product
 * cannot produce is the same kind of untrue claim Principle IV forbids a
 * generated document.
 */

/** A heading, in the small lettering the whole page uses for them. */
function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-faint">{children}</h2>
  );
}

export default async function Home({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  // Without this next-intl reads the request headers, which would force every
  // page to render dynamically. Server-first rendering is a constitution
  // requirement, so each page sets the locale explicitly.
  setRequestLocale(locale);
  const t = await getTranslations("home");
  const nav = await getTranslations("profile");

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-20 border-b border-cream-200 bg-cream-50/90 backdrop-blur-xl dark:border-white/10 dark:bg-[#081726]/80">
        <div className="mx-auto flex max-w-6xl items-center gap-5 px-6 py-3">
          <Wordmark compact />
          <nav className="-mx-1 hidden min-w-0 flex-1 items-center gap-1 overflow-x-auto px-1 md:flex">
            {PROFILE_LINKS.slice(0, 5).map(({ href, label }) => (
              <Link
                key={href}
                href={`/${locale}/profile${href}`}
                className="whitespace-nowrap rounded-full px-3 py-1.5 text-sm text-ink-soft transition hover:bg-cream-200 hover:text-warm-deep dark:text-brand-100/80 dark:hover:bg-white/10"
              >
                {nav(label)}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 md:ml-0">
            <LocaleSwitcher />
            <Link href={`/${locale}/profile`} className="btn-primary px-4 py-2 text-sm">
              {t("start")}
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* --- the world --------------------------------------------------
            Full width, with the words on the sky at the left the way a
            poster carries them, and stacked above the drawing where there
            is no room beside it. */}
        <section className="relative">
          <div className="relative">
            <World locale={locale} />

            {/* The words lie over the drawing, so this band spans the page —
                which would swallow every click on a marker underneath it.
                Only the column that holds the words takes the pointer. */}
            <div className="pointer-events-none mx-auto mt-6 flex max-w-6xl animate-rise flex-col items-start gap-4 px-6 lg:absolute lg:inset-x-0 lg:top-36 lg:mt-0">
              <div className="pointer-events-auto flex max-w-md flex-col items-start gap-4">
                <h1 className="text-pretty text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
                  {t("headline")}
                </h1>
                <p className="max-w-md text-base leading-relaxed text-ink-soft lg:rounded-2xl lg:bg-cream-50/80 lg:p-3 lg:backdrop-blur-sm dark:text-brand-100/80">
                  {t("lead")}
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-3">
                  <Link href={`/${locale}/profile`} className="btn-primary">
                    {t("start")}
                  </Link>
                  <Link
                    href={`/${locale}/profile/documents/rirekisho`}
                    className="btn-secondary bg-cream-50/90"
                  >
                    {t("generate")}
                  </Link>
                </div>
                <p className="hidden rounded-full bg-white/80 px-3 py-1 text-xs text-ink-faint backdrop-blur-sm sm:block">
                  {t("worldHint")}
                </p>
              </div>
            </div>
          </div>
        </section>

        <div className="mx-auto flex max-w-6xl flex-col gap-20 px-6 pb-24 pt-16">
          {/* --- how it works, as three stops on a path -------------------- */}
          <section className="flex flex-col gap-6">
            <SectionTitle>{t("howTitle")}</SectionTitle>
            <ol className="relative grid gap-6 sm:grid-cols-3">
              {/* the path between the stops, drawn behind them */}
              <div
                aria-hidden
                className="absolute left-[16%] right-[16%] top-6 hidden border-t-2 border-dashed border-cream-300 sm:block"
              />
              {STEPS.map((step, index) => (
                <li key={step} className="relative flex flex-col items-start gap-3">
                  <span className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-cream-300 bg-cream-50 text-base font-semibold tabular-nums text-warm shadow-[0_6px_16px_-10px_rgba(95,106,115,0.6)]">
                    {index + 1}
                  </span>
                  <h3 className="text-base font-semibold">{t(`steps.${step}.title`)}</h3>
                  <p className="text-sm leading-relaxed text-ink-soft dark:text-brand-100/75">
                    {t(`steps.${step}.body`)}
                  </p>
                </li>
              ))}
            </ol>
          </section>

          {/* --- the rooms of the house, as doors you can open -------------- */}
          <section className="flex flex-col gap-6">
            <SectionTitle>{t("availableTitle")}</SectionTitle>
            <ul className="grid gap-5 sm:grid-cols-2">
              {AVAILABLE.map(({ key, href }) => {
                const Glyph = GLYPHS[key];
                return (
                  <li key={key}>
                    <Link
                      href={`/${locale}/${href}`}
                      className="glass group flex h-full items-start gap-4 rounded-card p-6 transition duration-300 hover:-translate-y-1 hover:border-warm-soft hover:shadow-lift"
                    >
                      <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border-2 border-cream-300 bg-cream-100 text-warm-deep transition group-hover:border-warm-soft dark:border-white/10 dark:bg-white/5 dark:text-brand-200">
                        <Glyph className="h-6 w-6" />
                      </span>
                      <span className="flex flex-col gap-1">
                        <span className="text-base font-semibold">
                          {t(`available.${key}.title`)}
                        </span>
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

          {/* --- where it started, with the drawing that started it --------- */}
          <section className="grid items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,21rem)]">
            <DeskScene className="w-full" />
            <div className="flex flex-col gap-4">
              <SectionTitle>{t("makersTitle")}</SectionTitle>
              <p className="text-sm leading-relaxed text-ink-soft dark:text-brand-100/75">
                {t("since")}
              </p>
              <ul className="flex flex-col gap-3">
                {[
                  { key: "josh", Portrait: Josh },
                  { key: "mich", Portrait: Mich },
                ].map(({ key, Portrait }) => (
                  <li key={key} className="flex items-center gap-3">
                    <Portrait className="h-12 w-12 shrink-0" />
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold">{t(`makers.${key}.name`)}</span>
                      <span className="text-sm text-ink-soft dark:text-brand-100/75">
                        {t(`makers.${key}.role`)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
              {/* The cat had a line in the 2018 About screen. It keeps it. */}
              <span className="flex items-center gap-2">
                <Cat className="h-8 w-10" />
                <span className="rounded-full border border-cream-300 bg-cream-50 px-3 py-1 text-xs text-ink-soft dark:border-white/10 dark:bg-white/5 dark:text-brand-100/75">
                  {t("makers.cat")}
                </span>
              </span>
            </div>
          </section>

          {/* --- what is still being built ---------------------------------- */}
          <section className="flex flex-col gap-4">
            <SectionTitle>{t("plannedTitle")}</SectionTitle>
            <div className="rounded-card border-2 border-dashed border-cream-300 bg-cream-50/60 p-6 dark:border-white/10 dark:bg-white/5">
              <p className="text-sm text-ink-soft dark:text-brand-100/75">{t("plannedBody")}</p>
              <ul className="mt-4 flex flex-wrap gap-2">
                {PLANNED.map((item) => (
                  <li
                    key={item}
                    className="rounded-full border border-cream-300 bg-cream-100 px-3 py-1 text-sm text-ink-soft dark:border-white/10 dark:bg-white/5 dark:text-brand-100/75"
                  >
                    {t(`planned.${item}`)}
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {/* --- the promise, on a note -------------------------------------- */}
          <section className="glass flex flex-col gap-3 rounded-card p-7">
            <h2 className="text-lg font-semibold">{t("truthTitle")}</h2>
            <p className="max-w-2xl text-sm leading-relaxed text-ink-soft dark:text-brand-100/75">
              {t("truthBody")}
            </p>
          </section>

          <footer className="flex items-center gap-3 border-t border-cream-200 pt-6 text-xs text-ink-faint dark:border-white/10">
            <BrandMark className="h-5 w-5" gradientId="sj-footer" />
            <span>{t("since")}</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
