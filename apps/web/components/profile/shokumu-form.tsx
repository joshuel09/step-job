"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import {
  api,
  ApiError,
  ValidationError,
  type GeneratedDocument,
  type ShokumuRequest,
} from "@/lib/api";

import {
  Field,
  Problem,
  problemMessage,
  Select,
  toFieldErrors,
  type FieldErrors,
} from "./form-primitives";

/** Generate a profile-derived PDF and release its preview URL when replaced. */
export function ShokumuForm() {
  const t = useTranslations("profile.shokumu");
  const tc = useTranslations("common");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [problem, setProblem] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<GeneratedDocument | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!result) return;
    const url = URL.createObjectURL(result.blob);
    setPreviewUrl(url);
    return () => {
      URL.revokeObjectURL(url);
      setPreviewUrl(null);
    };
  }, [result]);

  /** Preserve generation errors until the user retries. */
  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrors({});
    setProblem(null);
    setResult(null);
    const data = new FormData(event.currentTarget);
    const options: ShokumuRequest = {
      arrangement: String(data.get("arrangement")) as ShokumuRequest["arrangement"],
      date_convention: String(data.get("date_convention")) as ShokumuRequest["date_convention"],
      paper_size: String(data.get("paper_size")) as ShokumuRequest["paper_size"],
    };
    try {
      setResult(await api.generateShokumuKeirekisho(options));
    } catch (error) {
      if (error instanceof ValidationError && error.failures.length > 0) {
        const fields = toFieldErrors(error.failures);
        for (const name of ["arrangement", "date_convention", "paper_size"]) {
          if (fields[name]) fields[name] = t("invalidChoice");
        }
        setErrors(fields);
      } else if (error instanceof ApiError && error.status === 404) setProblem(t("noProfile"));
      else setProblem(problemMessage(error, tc));
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="surface flex flex-col gap-5">
      <div>
        <h2 className="surface-title">{t("title")}</h2>
        <p className="explain">{t("explanation")}</p>
      </div>
      <p className="notice">{t("contentNote")}</p>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <fieldset disabled={pending} className="grid gap-4 sm:grid-cols-3">
          <Field name="arrangement" label={t("arrangement")} errors={errors}>
            <Select name="arrangement" defaultValue="reverse_chronological" errors={errors}>
              <option value="reverse_chronological">{t("newestFirst")}</option>
              <option value="chronological">{t("oldestFirst")}</option>
            </Select>
          </Field>
          <Field name="date_convention" label={t("dateConvention")} errors={errors}>
            <Select name="date_convention" defaultValue="seireki" errors={errors}>
              <option value="seireki">{t("westernDates")}</option>
              <option value="wareki">{t("eraDates")}</option>
            </Select>
          </Field>
          <Field name="paper_size" label={t("paperSize")} errors={errors}>
            <Select name="paper_size" defaultValue="a4" errors={errors}>
              <option value="a4">{t("a4")}</option>
              <option value="b5">{t("b5")}</option>
            </Select>
          </Field>
        </fieldset>
        {Object.entries(errors)
          .filter(([field]) => !["arrangement", "date_convention", "paper_size"].includes(field))
          .map(([field]) => (
            <p key={field} role="alert" className="field-error">
              {field === "identity"
                ? t("nameRequired")
                : field === "experiences"
                  ? t("experienceRequired")
                  : t("missingOther")}
            </p>
          ))}
        <Problem message={problem} />
        <button
          type="submit"
          disabled={pending}
          className="btn-primary self-start disabled:opacity-60"
        >
          {pending ? t("generating") : t("generate")}
        </button>
      </form>
      {result && previewUrl && (
        <div
          role="status"
          className="entry flex flex-col gap-3 border-brand-200 bg-brand-50/60 p-4"
        >
          <div className="flex flex-wrap items-center gap-3">
            <a href={previewUrl} download={result.filename} className="btn-form">
              {t("download")}
            </a>
            <a href={previewUrl} target="_blank" rel="noopener noreferrer" className="link text-sm">
              {t("preview")}
            </a>
          </div>
          <p>{t("pageCount", { count: result.pages })}</p>
          <p className="hint">{t("notStored")}</p>
          {result.snapshotId && (
            <p className="hint break-all">{t("snapshot", { id: result.snapshotId })}</p>
          )}
        </div>
      )}
    </section>
  );
}
