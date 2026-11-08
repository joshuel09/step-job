import { getTranslations, setRequestLocale } from "next-intl/server";

import { PageHeading } from "@/components/profile/page-heading";
import { ResumeForm } from "@/components/profile/resume-form";
import { ResumeReadiness } from "@/components/profile/resume-readiness";

export const dynamic = "force-dynamic";

/** Render the localized English resume workflow and its current readiness. */
export default async function ResumePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile.resume");

  return (
    <main className="page">
      <PageHeading
        title={t("pageTitle")}
        subtitle={t("pageSubtitle")}
        back={{ href: `/${locale}/profile`, label: t("back") }}
      />
      <ResumeReadiness locale={locale} />
      <ResumeForm />
    </main>
  );
}
