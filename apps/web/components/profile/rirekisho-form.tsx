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

import { Field, Section, Select, SubmitButton, toFieldErrors, type FieldErrors } from "./form-primitives";

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

export function RirekishoForm() {
  const t = useTranslations("profile.rirekisho");
  const [errors, setErrors] = useState<FieldErrors>({});
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
      else throw error;
    } finally {
      setPending(false);
    }
  }

  return (
    <Section title={t("title")}>
      <p className="mb-3 text-sm opacity-80">{t("explanation")}</p>
      {/* Said before generating, not discovered after printing. */}
      <p className="mb-4 text-xs opacity-70">{t("photoNote")}</p>

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
            <p key={field} role="alert" className="text-xs text-red-600 dark:text-red-400">
              {reason}
            </p>
          ))}

        <div>
          <SubmitButton pending={pending}>{pending ? t("generating") : t("generate")}</SubmitButton>
        </div>
      </form>

      {result && previewUrl && (
        <div className="mt-5 flex flex-col gap-3 border-t border-neutral-200 pt-4 dark:border-neutral-800">
          <div className="flex flex-wrap items-center gap-3">
            <a
              href={previewUrl}
              download={result.filename}
              className="rounded bg-neutral-900 px-4 py-2 text-sm text-white dark:bg-white dark:text-neutral-900"
            >
              {t("download")}
            </a>
            <a href={previewUrl} target="_blank" rel="noopener noreferrer" className="text-sm underline">
              {t("preview")}
            </a>
          </div>

          {/* A history that does not fit the conventional two pages produces
              more pages rather than losing entries, so the user is told
              instead of finding out at the printer (FR-018a). */}
          {result.pages > 2 && (
            <p className="text-xs opacity-80">{t("longDocument", { count: result.pages })}</p>
          )}

          <p className="text-xs opacity-70">{t("notStored")}</p>

          {result.snapshotId && (
            <p className="text-xs opacity-60">
              {t("snapshot", { id: result.snapshotId.slice(0, 8) })}
            </p>
          )}
        </div>
      )}
    </Section>
  );
}
