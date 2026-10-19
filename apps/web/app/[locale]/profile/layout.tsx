import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";
import type { ReactNode } from "react";

import { Wordmark } from "@/components/brand/wordmark";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { PROFILE_LINKS } from "@/lib/site";

/**
 * One navigation bar for every page under /profile.
 *
 * It was a row of links inside the profile page itself, which meant the other
 * five pages had no navigation at all and the row competed with the page
 * title for the same line — below about 1100px it wrapped mid-label, and
 * 履歴書 broke between characters into a vertical stack (#126).
 *
 * Here instead, so each page keeps its own heading and none of them repeat
 * this. The links scroll sideways rather than wrapping when the window is
 * narrow: a label that breaks in the middle is worse than one you scroll to,
 * and 履歴書 has no break point a reader would accept.
 */

export default async function ProfileLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile");

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 border-b border-white/50 bg-white/70 backdrop-blur-xl dark:border-white/10 dark:bg-[#081726]/70">
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-6 py-3">
          <Link href={`/${locale}`} className="shrink-0" aria-label="Step Job">
            <Wordmark compact />
          </Link>

          <nav className="-mx-1 flex min-w-0 flex-1 items-center gap-1 overflow-x-auto px-1 [mask-image:linear-gradient(to_right,black_calc(100%-2rem),transparent)] sm:[mask-image:none]">
            {PROFILE_LINKS.map(({ href, label }) => (
              <Link
                key={href}
                href={`/${locale}/profile${href}`}
                className="whitespace-nowrap rounded-full px-3 py-1.5 text-sm text-ink-soft transition hover:bg-brand-50 hover:text-brand-700 dark:text-brand-100/80 dark:hover:bg-white/10 dark:hover:text-brand-100"
              >
                {t(label)}
              </Link>
            ))}
          </nav>

          <div className="shrink-0">
            <LocaleSwitcher />
          </div>
        </div>
      </header>

      {children}
    </div>
  );
}
