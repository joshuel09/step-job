import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";

import { ImportForm } from "@/components/profile/import-form";
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
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <header>
        <Link href={`/${locale}/profile`} className="text-sm underline opacity-70">
          {t("back")}
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{t("title")}</h1>
        <p className="mt-1 text-sm opacity-70">{t("subtitle")}</p>
      </header>

      <ImportForm />

      {history.length > 0 && (
        <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
          <h2 className="mb-3 text-lg font-semibold">{t("historyTitle")}</h2>
          {/* Source kind and time only. The filename is never kept — a name can
              reveal where someone was applying (FR-019b). */}
          <ul className="flex flex-col gap-2 text-sm">
            {history.map((record) => (
              <li key={record.id} className="flex items-center justify-between gap-3">
                <span>{t(`sources.${record.source_kind}`)}</span>
                <span className="text-xs opacity-70">
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
        <Link href={`/${locale}/profile/review`} className="underline">
          {t("goToReview")}
        </Link>
      </p>
    </main>
  );
}
