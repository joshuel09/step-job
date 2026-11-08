"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { api, ValidationError, type GeneratedDocument, type ResumeRequest } from "@/lib/api";

import {
  Field,
  Problem,
  problemMessage,
  Select,
  toFieldErrors,
  type FieldErrors,
} from "./form-primitives";

/** Generate a profile-derived PDF and release its preview URL when replaced. */
export function ResumeForm() {
  const t = useTranslations("profile.resume");
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
    const options: ResumeRequest = {
      paper_size: String(data.get("paper_size")) as ResumeRequest["paper_size"],
      include_skills: data.get("include_skills") === "on",
    };
    try {
      setResult(await api.generateResume(options));
    } catch (error) {
      if (error instanceof ValidationError && error.failures.length > 0) {
        const fields = toFieldErrors(error.failures);
        if (fields.paper_size) fields.paper_size = t("invalidPaper");
        setErrors(fields);
      } else setProblem(problemMessage(error, tc));
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
      <p className="notice">{t("privacyNote")}</p>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field name="paper_size" label={t("paperSize")} errors={errors}>
          <Select name="paper_size" defaultValue="letter" errors={errors} disabled={pending}>
            <option value="letter">{t("letter")}</option>
            <option value="a4">{t("a4")}</option>
          </Select>
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="include_skills" defaultChecked disabled={pending} />
          {t("includeSkills")}
        </label>
        {Object.entries(errors)
          .filter(([field]) => field !== "paper_size")
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
