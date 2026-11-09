import { getTranslations, setRequestLocale } from "next-intl/server";

import { PageHeading } from "@/components/profile/page-heading";
import { TranslationReview } from "@/components/profile/translation-review";
import { api, ApiError, type ResumeReadinessReport } from "@/lib/api";

export const dynamic = "force-dynamic";

/** Load the current translation worklist without calling a model or writing data. */
export default async function TranslationsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile.translations");
  let report: ResumeReadinessReport | null = null;
  let failure: "missing" | "unavailable" | null = null;
  try {
    report = await api.resumeReadiness();
  } catch (error) {
    failure = error instanceof ApiError && error.status === 404 ? "missing" : "unavailable";
  }
  return (
    <main className="page">
      <PageHeading
        title={t("title")}
        subtitle={t("explanation")}
        back={{ href: `/${locale}/profile`, label: t("back") }}
      />
      <TranslationReview report={report} failure={failure} locale={locale} />
    </main>
  );
}
