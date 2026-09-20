"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ValidationError, type CareerStory, type WorkExperience } from "@/lib/api";

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

/**
 * Career stories: challenge, action, result (FR-007).
 *
 * The four fields are prompted separately rather than as one free-text box,
 * because a story that is retrievable and reusable six months later needs
 * structure — that is what makes it a STAR example rather than a note.
 */
export function StoryForm({
  existing,
  experiences,
}: {
  existing: CareerStory[];
  experiences: WorkExperience[];
}) {
  const t = useTranslations("profile.stories");
  const tc = useTranslations("common");
  const router = useRouter();
  const [errors, setErrors] = useState<FieldErrors>({});
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrors({});

    const form = new FormData(event.currentTarget);
    const body = {
      work_experience_id: form.get("work_experience_id") || null,
      title: form.get("title"),
      challenge: form.get("challenge"),
      action: form.get("action"),
      result: form.get("result"),
      source_language: form.get("source_language") ?? "en",
    };

    try {
      await api.createStory(body);
      (event.target as HTMLFormElement).reset();
      router.refresh();
    } catch (error) {
      if (error instanceof ValidationError) setErrors(toFieldErrors(error.failures));
      else throw error;
    } finally {
      setPending(false);
    }
  }

  async function onDelete(id: string) {
    await api.deleteStory(id);
    router.refresh();
  }

  return (
    <Section title={t("title")}>
      <p className="mb-3 text-xs opacity-70">{t("explanation")}</p>

      {existing.length > 0 && (
        <ul className="mb-4 flex flex-col gap-2">
          {existing.map((story) => (
            <li
              key={story.id}
              className="rounded border border-neutral-200 p-3 text-sm dark:border-neutral-800"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="font-medium">{story.title}</p>
                <button
                  type="button"
                  onClick={() => onDelete(story.id!)}
                  className="text-xs underline opacity-70"
                >
                  {tc("delete")}
                </button>
              </div>
              <dl className="mt-2 flex flex-col gap-1 text-xs opacity-80">
                <div>
                  <dt className="inline font-medium">{t("challenge")}: </dt>
                  <dd className="inline">{story.challenge}</dd>
                </div>
                <div>
                  <dt className="inline font-medium">{t("action")}: </dt>
                  <dd className="inline">{story.action}</dd>
                </div>
                <div>
                  <dt className="inline font-medium">{t("result")}: </dt>
                  <dd className="inline">{story.result}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <Field label={t("titleField")} name="title" errors={errors}>
          <TextInput name="title" errors={errors} required />
        </Field>

        <Field label={t("linkedRole")} name="work_experience_id" errors={errors} hint={t("linkedRoleHint")}>
          <Select name="work_experience_id" errors={errors} defaultValue="">
            <option value="">{t("noRole")}</option>
            {experiences.map((experience) => (
              <option key={experience.id} value={experience.id}>
                {experience.job_title} — {experience.employer_name}
              </option>
            ))}
          </Select>
        </Field>

        <Field label={t("challenge")} name="challenge" errors={errors} hint={t("challengeHint")}>
          <TextArea name="challenge" rows={2} errors={errors} required />
        </Field>

        <Field label={t("action")} name="action" errors={errors} hint={t("actionHint")}>
          <TextArea name="action" rows={2} errors={errors} required />
        </Field>

        <Field label={t("result")} name="result" errors={errors} hint={t("resultHint")}>
          <TextArea name="result" rows={2} errors={errors} required />
        </Field>

        <Field label={t("sourceLanguage")} name="source_language" errors={errors}>
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
