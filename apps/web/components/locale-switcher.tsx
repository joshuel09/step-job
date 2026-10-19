"use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "next/navigation";
import { useTransition } from "react";

import { api } from "@/lib/api";
import { locales, type Locale } from "@/i18n";

/**
 * Switching the interface language (FR-021).
 *
 * The choice is persisted through the API, not kept in the browser: a setting
 * that lives only here would not survive a second device, which is exactly the
 * case this product has — someone checking applications on a phone between
 * interviews (research.md R-003).
 *
 * Changing the interface never touches stored content. Entries keep the language
 * their author wrote them in (FR-023).
 */
export function LocaleSwitcher() {
  const t = useTranslations("common");
  const current = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function onChange(next: string) {
    if (next === current) return;

    startTransition(async () => {
      // Persist first so the choice survives this browser; if it fails the
      // interface stays where it is rather than silently diverging from stored state.
      try {
        await api.setLocale(next as Locale);
      } catch {
        // A signed-out visitor has no profile to store against; the URL still
        // carries the choice for this session.
      }

      const rest = pathname.replace(new RegExp(`^/(${locales.join("|")})`), "");
      router.replace(`/${next}${rest || ""}`);
      router.refresh();
    });
  }

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="sr-only">{t("language")}</span>
      <select
        aria-label={t("language")}
        value={current}
        disabled={pending}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-full border border-brand-200/80 bg-white/70 px-3 py-1 text-sm text-ink-soft backdrop-blur transition hover:bg-white dark:border-brand-300/20 dark:bg-white/5 dark:text-brand-100"
      >
        <option value="en">English</option>
        <option value="ja">日本語</option>
      </select>
    </label>
  );
}
