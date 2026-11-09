import { getTranslations, setRequestLocale } from "next-intl/server";
import { PageHeading } from "@/components/profile/page-heading";
import { ShokumuForm } from "@/components/profile/shokumu-form";

export const dynamic = "force-dynamic";

/** Generate a career history document from the existing profile. */
export default async function ShokumuPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile.shokumu");
  return (
    <main className="page">
      <PageHeading
        title={t("pageTitle")}
        subtitle={t("pageSubtitle")}
        back={{ href: `/${locale}/profile`, label: t("back") }}
      />
      <ShokumuForm />
    </main>
  );
}
