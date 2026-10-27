import { getTranslations, setRequestLocale } from "next-intl/server";

import { PageHeading } from "@/components/profile/page-heading";
import { RirekishoForm } from "@/components/profile/rirekisho-form";
import { RirekishoReadiness } from "@/components/profile/rirekisho-readiness";

export const dynamic = "force-dynamic";

export default async function RirekishoPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile.rirekisho");

  return (
    <main className="page">
      <PageHeading
        title={t("pageTitle")}
        subtitle={t("pageSubtitle")}
        back={{ href: `/${locale}/profile`, label: t("back") }}
      />

      {/* Above the button on purpose: what the document will be missing is
          worth knowing before it is generated, not after it is printed. */}
      <RirekishoReadiness locale={locale} />

      <RirekishoForm />

      {/* The sections a 履歴書 has that this product deliberately does not fill
          in. Saying so here means the blank is a decision the user can see
          rather than something that looks like a bug. */}
      <section className="surface text-sm">
        <h2 className="mb-2 text-base font-semibold text-ink">{t("leftToYouTitle")}</h2>
        <p className="text-ink-soft">{t("leftToYou")}</p>
      </section>
    </main>
  );
}
