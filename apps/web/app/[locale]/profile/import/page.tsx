import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";

import { ImportForm } from "@/components/profile/import-form";
import { PageHeading } from "@/components/profile/page-heading";
import { api, type CareerImport } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ImportPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile.import");

  let history: CareerImport[] = [];
  try {
    history = await api.listImports();
  } catch {
    // No profile yet is a normal starting state.
  }

  return (
    <main className="page">
      <PageHeading
        title={t("title")}
        subtitle={t("subtitle")}
        back={{ href: `/${locale}/profile`, label: t("back") }}
      />

      <ImportForm />

      {history.length > 0 && (
        <section className="surface">
          <h2 className="surface-title">{t("historyTitle")}</h2>
          {/* Source kind and time only. The filename is never kept — a name can
              reveal where someone was applying (FR-019b). */}
          <ul className="flex flex-col gap-2 text-sm">
            {history.map((record) => (
              <li key={record.id} className="flex items-center justify-between gap-3">
                <span>{t(`sources.${record.source_kind}`)}</span>
                <span className="hint">
                  {new Date(record.started_at).toLocaleString()} ·{" "}
                  {record.status === "completed"
                    ? t("found", { count: record.entry_count })
                    : t(`statuses.${record.status}`)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="text-sm">
        <Link href={`/${locale}/profile/review`} className="link">
          {t("goToReview")}
        </Link>
      </p>
    </main>
  );
}
