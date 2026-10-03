import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";

import { RirekishoForm } from "@/components/profile/rirekisho-form";

export const dynamic = "force-dynamic";

export default async function RirekishoPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile.rirekisho");

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <header>
        <Link href={`/${locale}/profile`} className="text-sm underline opacity-70">
          {t("back")}
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{t("pageTitle")}</h1>
        <p className="mt-1 text-sm opacity-70">{t("pageSubtitle")}</p>
      </header>

      <RirekishoForm />

      {/* The sections a 履歴書 has that this product deliberately does not fill
          in. Saying so here means the blank is a decision the user can see
          rather than something that looks like a bug. */}
      <section className="rounded-lg border border-neutral-200 p-4 text-sm dark:border-neutral-800">
        <h2 className="mb-2 text-base font-semibold">{t("leftToYouTitle")}</h2>
        <p className="opacity-80">{t("leftToYou")}</p>
      </section>
    </main>
  );
}
