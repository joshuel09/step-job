import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { ApiError, api, type ReadinessReport } from "@/lib/api";

/**
 * What the document will be missing, said before it is generated.
 *
 * A 履歴書 is printed and handed over. Learning at the printer that a box is
 * blank, or that a university reads in English, is too late to do anything
 * about — so the three things the API separates are separated here too, and
 * they ask for three different responses (FR-022c):
 *
 * - **required**: the document cannot be produced at all until these are filled.
 * - **blank**: it will be produced, with an empty box where these would go.
 * - **English**: it will be produced, with these printed as they were written.
 *
 * Nothing here writes anything. The user goes to their profile and decides; an
 * entry is never translated on their behalf (research.md R-001).
 *
 * Rendered on the server so the report is already on the page when it opens,
 * rather than appearing under the button a moment after it has been read past.
 */

/** The field names the report uses, under the keys the catalogues hold. */
const FIELD_KEYS: Record<string, string> = {
  identity: "identity",
  "identity.full_name_latin": "fullNameLatin",
  "identity.furigana": "furigana",
  "identity.date_of_birth": "dateOfBirth",
  "identity.address": "address",
  "identity.phone": "phone",
  "identity.email": "email",
  education: "education",
  experiences: "experiences",
  certifications: "certifications",
};

type Readiness =
  | { state: "report"; report: ReadinessReport }
  /** Nothing recorded yet, so there is no profile to check. */
  | { state: "nothing" }
  /** The check itself failed. Said rather than hidden: a silent failure here
      would read as "nothing is missing", which is the one thing it must not
      claim without having looked. */
  | { state: "unchecked" };

async function load(): Promise<Readiness> {
  try {
    return { state: "report", report: await api.rirekishoReadiness() };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return { state: "nothing" };
    return { state: "unchecked" };
  }
}

export async function RirekishoReadiness({ locale }: { locale: string }) {
  const t = await getTranslations("profile.rirekisho.readiness");
  const readiness = await load();

  /** An unknown field name is shown as it came, rather than as a blank line. */
  const label = (field: string) => (FIELD_KEYS[field] ? t(`fields.${FIELD_KEYS[field]}`) : field);

  const toProfile = (
    <Link href={`/${locale}/profile`} className="link text-sm">
      {t("fix")}
    </Link>
  );

  const report = readiness.state === "report" ? readiness.report : null;
  const settled =
    report !== null &&
    report.missing_optional.length === 0 &&
    report.entries_without_japanese.length === 0;

  return (
    <section className="surface flex flex-col gap-4">
      <div>
        <h2 className="surface-title mb-1">{t("title")}</h2>
        <p className="explain">{t("explanation")}</p>
      </div>

      {readiness.state === "unchecked" && <p className="field-error">{t("unchecked")}</p>}

      {readiness.state === "nothing" && (
        <div className="notice flex flex-col items-start gap-2">
          <p>{t("nothingRecorded")}</p>
          {toProfile}
        </div>
      )}

      {/* The refusal the user would otherwise meet by pressing the button. It
          comes from the same rule the generator refuses by, so this cannot
          promise a document that would then be declined (FR-015). */}
      {report && report.missing_required.length > 0 && (
        <div className="notice flex flex-col items-start gap-2">
          <p className="font-medium">{t("blockedTitle")}</p>
          <ul className="list-disc pl-5">
            {report.missing_required.map((field) => (
              <li key={field}>{label(field)}</li>
            ))}
          </ul>
          {toProfile}
        </div>
      )}

      {report?.can_generate && settled && <p className="explain">{t("ready")}</p>}

      {report && report.missing_optional.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-medium text-ink">{t("blankTitle")}</h3>
          <p className="hint">{t("blankExplanation")}</p>
          <ul className="flex flex-wrap gap-2">
            {report.missing_optional.map((field) => (
              <li key={field} className="entry px-2.5 py-1 text-xs">
                {label(field)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {report && report.entries_without_japanese.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-medium text-ink">{t("englishTitle")}</h3>
          <p className="hint">{t("englishExplanation")}</p>
          <ul className="flex flex-col gap-2">
            {report.entries_without_japanese.map((entry) => (
              <li key={entry.entry_id} className="entry">
                {/* The entry's own text, so the user can tell which one this
                    is without going to look it up, and the kind under it
                    rather than beside it: read aloud, the two run together. */}
                <p className="font-medium">{entry.label}</p>
                <p className="hint mt-0.5">{t(`entryTypes.${entry.entry_type}`)}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* One way to act on all of it. Not repeated when the block above
          already carries it. */}
      {report && report.missing_required.length === 0 && !settled && <div>{toProfile}</div>}
    </section>
  );
}
