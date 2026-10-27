"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import {
  api,
  ValidationError,
  type DateConvention,
  type GeneratedDocument,
  type PaperSize,
} from "@/lib/api";

import { GLYPHS } from "@/components/brand/icons";

import {
  Field,
  Problem,
  problemMessage,
  Select,
  toFieldErrors,
  type FieldErrors,
} from "./form-primitives";

/**
 * Producing a 履歴書.
 *
 * Nothing is stored, so there is no list of past documents to return to: the
 * file is handed over and that is the end of it. What persists is the record
 * of what the document was based on, which is why the snapshot is shown rather
 * than hidden — a user who sends a document to an employer can later ask what
 * it said.
 */
/** The fields this form renders, which show their own errors inline. */
const CHOICES = ["date_convention", "paper_size"];

const RirekishoGlyph = GLYPHS.rirekisho;

export function RirekishoForm() {
  const t = useTranslations("profile.rirekisho");
  const tc = useTranslations("common");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [problem, setProblem] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<GeneratedDocument | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // A blob URL holds the document in memory until it is released. Without
  // this, generating repeatedly would leak a full document each time.
  useEffect(() => {
    if (!result) return;
    const url = URL.createObjectURL(result.blob);
    setPreviewUrl(url);
    return () => {
      URL.revokeObjectURL(url);
      setPreviewUrl(null);
    };
  }, [result]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrors({});
    setProblem(null);
    setResult(null);

    const data = new FormData(event.currentTarget);

    try {
      setResult(
        await api.generateRirekisho({
          date_convention: String(data.get("date_convention")) as DateConvention,
          paper_size: String(data.get("paper_size")) as PaperSize,
        }),
      );
    } catch (error) {
      // A profile without a name names the field rather than failing
      // generically, so the user knows what to go and fix (FR-015).
      if (error instanceof ValidationError) setErrors(toFieldErrors(error.failures));
      else setProblem(problemMessage(error, tc));
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="surface flex flex-col gap-5">
      {/* The one page that produces what the product is for, so it opens with
          the same mark the landing page gives it. */}
      <div className="flex items-start gap-4">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border-2 border-cream-300 bg-cream-100 text-warm-deep">
          <RirekishoGlyph className="h-6 w-6" />
        </span>
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold text-ink">{t("title")}</h2>
          <p className="explain">{t("explanation")}</p>
        </div>
      </div>

      {/* Said before generating, not discovered after printing. */}
      <ul className="notice flex list-disc flex-col gap-1.5 pl-8 text-xs leading-relaxed">
        <li>{t("photoNote")}</li>
        <li>{t("englishNote")}</li>
        <li>{t("privateNote")}</li>
      </ul>

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field name="date_convention" label={t("dateConvention")} errors={errors}>
            <Select name="date_convention" errors={errors} defaultValue="seireki">
              <option value="seireki">{t("conventions.seireki")}</option>
              <option value="wareki">{t("conventions.wareki")}</option>
            </Select>
          </Field>

          <Field name="paper_size" label={t("paperSize")} errors={errors}>
            <Select name="paper_size" errors={errors} defaultValue="a4">
              <option value="a4">{t("papers.a4")}</option>
              <option value="b5">{t("papers.b5")}</option>
            </Select>
          </Field>
        </div>

        {/* What the form has no field for. A rejection usually names something
            in the profile — a missing name — rather than a choice made here,
            and that has to be shown somewhere or it is shown nowhere. */}
        {Object.entries(errors)
          .filter(([field]) => !CHOICES.includes(field))
          .map(([field, reason]) => (
            <p key={field} role="alert" className="field-error">
              {/* The server's reason is English. A missing name is the refusal a
                  user will actually meet, so it is said in their language. */}
              {field === "identity" || field.startsWith("identity.") ? t("nameRequired") : reason}
            </p>
          ))}

        <Problem message={problem} />

        <div>
          {/* The landing page's own button: this is the action the product
              exists for, and the one place a form earns it. */}
          <button type="submit" disabled={pending} className="btn-primary disabled:opacity-60">
            {pending ? t("generating") : t("generate")}
          </button>
        </div>
      </form>

      {result && previewUrl && (
        <div className="entry flex animate-rise flex-col gap-3 border-brand-200 bg-brand-50/60 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <a href={previewUrl} download={result.filename} className="btn-form">
              {t("download")}
            </a>
            <a href={previewUrl} target="_blank" rel="noopener noreferrer" className="link text-sm">
              {t("preview")}
            </a>
          </div>

          {/* A history that does not fit the conventional two pages produces
              more pages rather than losing entries, so the user is told
              instead of finding out at the printer (FR-018a). */}
          {result.pages > 2 && (
            <p className="text-xs font-medium text-brand-800">
              {t("longDocument", { count: result.pages })}
            </p>
          )}

          <p className="hint">{t("notStored")}</p>

          {result.snapshotId && (
            <p className="hint">{t("snapshot", { id: result.snapshotId.slice(0, 8) })}</p>
          )}
        </div>
      )}
    </section>
  );
}
