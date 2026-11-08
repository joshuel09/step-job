import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { api, type ResumeReadinessReport } from "@/lib/api";

/** Show profile gaps before generation without blocking on translation warnings. */
export async function ResumeReadiness({ locale }: { locale: string }) {
  const t = await getTranslations("profile.resume");
  let report: ResumeReadinessReport | null = null;
  try {
    report = await api.resumeReadiness();
  } catch {
    // A failed check must not look like a complete profile.
  }

  return (
    <section className="surface flex flex-col gap-4">
      <h2 className="surface-title">{t("readinessTitle")}</h2>
      {!report && <p className="notice">{t("unchecked")}</p>}
      {report && (
        <>
          {report.missing_required.length > 0 && (
            <div className="notice">
              <h3 className="font-medium">{t("missingTitle")}</h3>
              <ul className="list-disc pl-5">
                {report.missing_required.map((field) => (
                  <li key={field}>
                    {field === "identity"
                      ? t("nameRequired")
                      : field === "experiences"
                        ? t("experienceRequired")
                        : t("missingOther")}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.needs_english.length > 0 && (
            <div>
              <h3 className="text-sm font-medium">{t("needsEnglishTitle")}</h3>
              <p className="hint">{t("needsEnglishNote")}</p>
              <ul className="mt-2 flex flex-col gap-2">
                {report.needs_english.map((entry) => (
                  <li
                    key={`${entry.entry_type}:${entry.entry_id}:${entry.field}`}
                    className="entry"
                  >
                    <p className="font-medium">{entry.label}</p>
                    <p className="whitespace-pre-wrap">{entry.source_text}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.untranslated_names.length > 0 && (
            <div>
              <h3 className="text-sm font-medium">{t("namesTitle")}</h3>
              <p className="hint">{t("namesNote")}</p>
              <ul className="list-disc pl-5">
                {report.untranslated_names.map((entry) => (
                  <li key={`${entry.entry_type}:${entry.entry_id}:${entry.field}`}>
                    {entry.recorded_name}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.stale_translations.length > 0 && (
            <div>
              <h3 className="text-sm font-medium">{t("staleTitle")}</h3>
              <p className="hint">{t("staleNote")}</p>
              <ul className="mt-2 flex flex-col gap-2">
                {report.stale_translations.map((entry) => (
                  <li key={entry.id} className="entry whitespace-pre-wrap">
                    <p>
                      <span className="font-medium">{t("currentSource")}: </span>
                      {entry.source_text}
                    </p>
                    <p>
                      <span className="font-medium">{t("approvedEnglish")}: </span>
                      {entry.text}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.can_generate &&
            report.needs_english.length === 0 &&
            report.untranslated_names.length === 0 &&
            report.stale_translations.length === 0 && <p className="explain">{t("ready")}</p>}
        </>
      )}
      <Link href={`/${locale}/profile`} className="link self-start text-sm">
        {t("fixProfile")}
      </Link>
    </section>
  );
}
