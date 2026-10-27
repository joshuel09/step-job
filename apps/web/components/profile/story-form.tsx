"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ValidationError, type CareerStory, type WorkExperience } from "@/lib/api";

import {
  Field,
  Problem,
  Section,
  Select,
  SubmitButton,
  TextArea,
  TextInput,
  problemMessage,
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
  const [problem, setProblem] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrors({});
    setProblem(null);

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
      else setProblem(problemMessage(error, tc));
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
      <p className="hint mb-3">{t("explanation")}</p>

      {existing.length > 0 && (
        <ul className="mb-4 flex flex-col gap-2">
          {existing.map((story) => (
            <li key={story.id} className="entry">
              <div className="flex items-start justify-between gap-3">
                <p className="font-medium">{story.title}</p>
                <button type="button" onClick={() => onDelete(story.id!)} className="link text-xs">
                  {tc("delete")}
                </button>
              </div>
              <dl className="mt-2 flex flex-col gap-1 text-xs text-ink-soft">
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

        <Field
          label={t("linkedRole")}
          name="work_experience_id"
          errors={errors}
          hint={t("linkedRoleHint")}
        >
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

        <Problem message={problem} />

        <SubmitButton pending={pending}>{t("add")}</SubmitButton>
      </form>
    </Section>
  );
}
