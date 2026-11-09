import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { api, ApiError, type ShokumuReadinessReport } from "@/lib/api";

/** Keep API identifiers out of the localized readiness report. */
export const SHOKUMU_FIELDS: Record<string, string> = {
  identity: "identity",
  experiences: "experiences",
  skills: "skills",
  languages: "languages",
  certifications: "certifications",
  stories: "stories",
};

/** Readiness is advisory; the API remains responsible for generation refusals. */
export async function ShokumuReadiness({ locale }: { locale: string }) {
  const t = await getTranslations("profile.shokumu");
  let report: ShokumuReadinessReport | null = null;
  let missing = false;
  try {
    report = await api.shokumuReadiness();
  } catch (error) {
    missing = error instanceof ApiError && error.status === 404;
  }
  const label = (field: string) => t(`fields.${SHOKUMU_FIELDS[field] ?? "other"}`);
  return (
    <section className="surface flex flex-col gap-3">
      <h2 className="surface-title">{t("readinessTitle")}</h2>
      {!report && <p className="notice">{missing ? t("noProfile") : t("unchecked")}</p>}
      {report && (
        <>
          {report.missing_required.length > 0 && (
            <div className="notice">
              <h3 className="font-medium">{t("requiredTitle")}</h3>
              <ul className="list-disc pl-5">
                {report.missing_required.map((field) => (
                  <li key={field}>{label(field)}</li>
                ))}
              </ul>
            </div>
          )}
          {report.missing_optional.length > 0 && (
            <div>
              <h3 className="text-sm font-medium">{t("optionalTitle")}</h3>
              <p className="hint">{t("optionalNote")}</p>
              <ul className="list-disc pl-5">
                {report.missing_optional.map((field) => (
                  <li key={field}>{label(field)}</li>
                ))}
              </ul>
            </div>
          )}
          {report.unattached_achievements.length > 0 && (
            <div>
              <h3 className="text-sm font-medium">{t("unattachedTitle")}</h3>
              <p className="hint">{t("unattachedNote")}</p>
              <ul className="list-disc pl-5">
                {report.unattached_achievements.map((entry) => (
                  <li key={entry.entry_id}>{entry.title}</li>
                ))}
              </ul>
              <Link href={`/${locale}/profile/stories`} className="link text-sm">
                {t("reviewStories")}
              </Link>
            </div>
          )}
          {report.can_generate &&
            report.missing_optional.length === 0 &&
            report.unattached_achievements.length === 0 && <p className="explain">{t("ready")}</p>}
        </>
      )}
      <Link href={`/${locale}/profile`} className="link self-start text-sm">
        {t("back")}
      </Link>
    </section>
  );
}
