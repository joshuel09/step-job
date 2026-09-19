"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ApiError, ValidationError, type WorkExperience } from "@/lib/api";

import {
  Field,
  Section,
  Select,
  SubmitButton,
  TextArea,
  TextInput,
  toFieldErrors,
  type FieldErrors,
} from "./form-primitives";

const EMPLOYMENT_TYPES = ["permanent", "contract", "part_time", "internship", "freelance"] as const;

export function ExperienceForm({ existing }: { existing: WorkExperience[] }) {
  const t = useTranslations("profile.experience");
  const router = useRouter();
  const [errors, setErrors] = useState<FieldErrors>({});
  const [pending, setPending] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrors({});

    const form = new FormData(event.currentTarget);
    const body = {
      employer_name: form.get("employer_name"),
      job_title: form.get("job_title"),
      employment_type: form.get("employment_type") || null,
      started_on: form.get("started_on"),
      // Left blank means the role is ongoing, not missing.
      ended_on: form.get("ended_on") || null,
      description: form.get("description") ?? "",
      source_language: form.get("source_language") ?? "en",
    };

    try {
      await api.createEntry<WorkExperience>("experiences", body);
      (event.target as HTMLFormElement).reset();
      router.refresh();
    } catch (error) {
      if (error instanceof ValidationError) setErrors(toFieldErrors(error.failures));
      else throw error;
    } finally {
      setPending(false);
    }
  }

  async function onDelete(id: string, confirm: boolean) {
    try {
      await api.deleteEntry("experiences", id, confirm);
      setConfirming(null);
      router.refresh();
    } catch (error) {
      // FR-013: a conflict means other records reference this entry, and the
      // user must be told before it is removed.
      if (error instanceof ApiError && error.status === 409) setConfirming(id);
      else throw error;
    }
  }

  return (
    <Section title={t("title")}>
      {existing.length > 0 && (
        <ul className="mb-4 flex flex-col gap-2">
          {existing.map((entry) => (
            <li
              key={entry.id}
              className="flex items-start justify-between gap-3 rounded border border-neutral-200 p-3 text-sm dark:border-neutral-800"
            >
              <div>
                <p className="font-medium">
                  {entry.job_title} — {entry.employer_name}
                </p>
                <p className="text-xs opacity-70">
                  {entry.started_on} – {entry.ended_on ?? t("present")}
                </p>
                {confirming === entry.id && (
                  <p role="alert" className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                    {t("deleteWarning")}{" "}
                    <button
                      type="button"
                      onClick={() => onDelete(entry.id!, true)}
                      className="underline"
                    >
                      {t("deleteAnyway")}
                    </button>
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => onDelete(entry.id!, false)}
                className="text-xs underline opacity-70"
              >
                {t("delete")}
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <Field label={t("employer")} name="employer_name" errors={errors}>
          <TextInput name="employer_name" errors={errors} required />
        </Field>

        <Field label={t("jobTitle")} name="job_title" errors={errors}>
          <TextInput name="job_title" errors={errors} required />
        </Field>

        <Field label={t("employmentType")} name="employment_type" errors={errors}>
          <Select name="employment_type" errors={errors} defaultValue="">
            <option value="">—</option>
            {EMPLOYMENT_TYPES.map((value) => (
              <option key={value} value={value}>
                {t(`employmentTypes.${value}`)}
              </option>
            ))}
          </Select>
        </Field>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label={t("startedOn")} name="started_on" errors={errors}>
            <TextInput name="started_on" type="date" errors={errors} required />
          </Field>
          <Field label={t("endedOn")} name="ended_on" errors={errors} hint={t("ongoingHint")}>
            <TextInput name="ended_on" type="date" errors={errors} />
          </Field>
        </div>

        <Field label={t("description")} name="description" errors={errors}>
          <TextArea name="description" errors={errors} />
        </Field>

        <Field label={t("sourceLanguage")} name="source_language" errors={errors} hint={t("sourceLanguageHint")}>
          <Select name="source_language" errors={errors} defaultValue="en">
            <option value="en">English</option>
            <option value="ja">日本語</option>
          </Select>
        </Field>

        <SubmitButton pending={pending}>{t("add")}</SubmitButton>
      </form>
    </Section>
  );
}
