import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";

import { DangerZone } from "@/components/profile/danger-zone";

export const dynamic = "force-dynamic";

export default async function SettingsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile.settings");

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <header>
        <Link href={`/${locale}/profile`} className="text-sm underline opacity-70">
          {t("back")}
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{t("title")}</h1>
      </header>

      <DangerZone />
    </main>
  );
}
