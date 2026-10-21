"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { PROFILE_LINKS } from "@/lib/site";

type ProfileLink = (typeof PROFILE_LINKS)[number];

/**
 * Links to the profile pages, with the one you are on marked.
 *
 * The overview is marked only on itself, not on every page under it, or it
 * would be marked everywhere.
 */
export function NavLinks({
  locale,
  links = PROFILE_LINKS,
  className = "",
}: {
  locale: string;
  links?: readonly ProfileLink[];
  className?: string;
}) {
  const t = useTranslations("profile");
  const pathname = usePathname();

  return (
    <nav className={`-mx-1 min-w-0 flex-1 items-center gap-1 overflow-x-auto px-1 ${className}`}>
      {links.map(({ href, label }) => {
        const target = `/${locale}/profile${href}`;
        const here = href === "" ? pathname === target : pathname.startsWith(target);
        return (
          <Link
            key={href}
            href={target}
            aria-current={here ? "page" : undefined}
            className="nav-link"
          >
            {t(label)}
          </Link>
        );
      })}
    </nav>
  );
}
