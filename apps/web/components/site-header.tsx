import Link from "next/link";
import type { ReactNode } from "react";

import { Wordmark } from "@/components/brand/wordmark";
import { LocaleSwitcher } from "@/components/locale-switcher";

/**
 * The bar across the top of every page: the wordmark home, whatever
 * navigation the page carries, the language control, and an optional action.
 *
 * The landing page and the profile pages each had their own copy, in two
 * styles, so walking from one to the other changed the frame round the
 * content (#125). One component keeps the front door and the rooms in the
 * same building.
 */
export function SiteHeader({
  locale,
  children,
  action,
}: {
  locale: string;
  /** The navigation, between the wordmark and the language control. */
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header className="site-header">
      <div className="mx-auto flex max-w-6xl items-center gap-5 px-6 py-3">
        <Link href={`/${locale}`} className="shrink-0" aria-label="Step Job">
          <Wordmark compact />
        </Link>
        {children}
        <div className="ml-auto flex shrink-0 items-center gap-3">
          <LocaleSwitcher />
          {action}
        </div>
      </div>
    </header>
  );
}
