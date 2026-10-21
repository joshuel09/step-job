import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { NavLinks } from "@/components/nav-links";
import { SiteHeader } from "@/components/site-header";

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

  return (
    <div className="min-h-dvh">
      <SiteHeader locale={locale}>
        {/* Scrolls sideways rather than wrapping when the window is narrow. */}
        <NavLinks
          locale={locale}
          className="flex [mask-image:linear-gradient(to_right,black_calc(100%-2rem),transparent)] sm:[mask-image:none]"
        />
      </SiteHeader>

      {children}
    </div>
  );
}
