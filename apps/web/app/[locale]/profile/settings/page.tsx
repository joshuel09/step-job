import { getTranslations, setRequestLocale } from "next-intl/server";

import { DangerZone } from "@/components/profile/danger-zone";
import { PageHeading } from "@/components/profile/page-heading";

export const dynamic = "force-dynamic";

export default async function SettingsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile.settings");

  return (
    <main className="page">
      <PageHeading title={t("title")} back={{ href: `/${locale}/profile`, label: t("back") }} />

      <DangerZone />
    </main>
  );
}
