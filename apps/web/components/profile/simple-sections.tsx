"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ValidationError } from "@/lib/api";

import {
  Field,
  Problem,
  Section,
  Select,
  SubmitButton,
  TextInput,
  problemMessage,
  toFieldErrors,
  type FieldErrors,
} from "./form-primitives";

type FieldSpec = { name: string; type?: string; required?: boolean; options?: string[] };

/**
 * Education, certifications, skills and languages share one shape: a list plus
 * a short add-form. Building them from a spec keeps the validation and delete
 * behaviour identical across all four rather than drifting per section.
 */
function ListSection({
  section,
  fields,
  entries,
  label,
}: {
  section: string;
  fields: FieldSpec[];
  entries: Record<string, unknown>[];
  label: (entry: Record<string, unknown>) => string;
}) {
  const t = useTranslations(`profile.${section}`);
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
    const body = Object.fromEntries([...form.entries()].map(([k, v]) => [k, v === "" ? null : v]));

    try {
      await api.createEntry(section, body);
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
    await api.deleteEntry(section, id);
    router.refresh();
  }

  return (
    <Section title={t("title")}>
      {entries.length > 0 && (
        <ul className="mb-4 flex flex-col gap-2">
          {entries.map((entry) => (
            <li
              key={String(entry.id)}
              className="entry flex items-center justify-between gap-3 py-2"
            >
              <span>{label(entry)}</span>
              <button
                type="button"
                onClick={() => onDelete(String(entry.id))}
                className="link text-xs"
              >
                {tc("delete")}
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        {fields.map(({ name, type = "text", required, options }) => (
          <Field key={name} label={t(name)} name={name} errors={errors}>
            {options ? (
              <Select name={name} errors={errors} required={required} defaultValue="">
                {!required && <option value="">—</option>}
                {options.map((value) => (
                  <option key={value} value={value}>
                    {t(`options.${value}`)}
                  </option>
                ))}
              </Select>
            ) : (
              <TextInput name={name} type={type} errors={errors} required={required} />
            )}
          </Field>
        ))}
        <Problem message={problem} />

        <SubmitButton pending={pending}>{tc("save")}</SubmitButton>
      </form>
    </Section>
  );
}

export function EducationSection({ entries }: { entries: Record<string, unknown>[] }) {
  return (
    <ListSection
      section="education"
      entries={entries}
      fields={[
        { name: "institution", required: true },
        { name: "qualification" },
        { name: "field_of_study" },
        { name: "started_on", type: "date" },
        { name: "ended_on", type: "date" },
      ]}
      label={(e) => [e.institution, e.qualification].filter(Boolean).join(" — ")}
    />
  );
}

export function CertificationSection({ entries }: { entries: Record<string, unknown>[] }) {
  return (
    <ListSection
      section="certifications"
      entries={entries}
      fields={[
        { name: "name", required: true },
        { name: "issuer" },
        { name: "issued_on", type: "date" },
        { name: "expires_on", type: "date" },
      ]}
      label={(e) => [e.name, e.issuer].filter(Boolean).join(" — ")}
    />
  );
}

export function SkillSection({ entries }: { entries: Record<string, unknown>[] }) {
  return (
    <ListSection
      section="skills"
      entries={entries}
      fields={[
        { name: "name", required: true },
        { name: "level", options: ["beginner", "intermediate", "advanced", "expert"] },
      ]}
      label={(e) => [e.name, e.level].filter(Boolean).join(" · ")}
    />
  );
}

export function LanguageSection({ entries }: { entries: Record<string, unknown>[] }) {
  return (
    <ListSection
      section="languages"
      entries={entries}
      fields={[
        { name: "language", required: true },
        {
          name: "proficiency",
          required: true,
          options: ["native", "business", "conversational", "basic"],
        },
        { name: "qualification" },
      ]}
      label={(e) => `${e.language} (${e.proficiency})`}
    />
  );
}
