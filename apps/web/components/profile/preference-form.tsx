"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { api, ValidationError, type CareerPreference } from "@/lib/api";

import {
  Field,
  Section,
  Select,
  SubmitButton,
  TextInput,
  toFieldErrors,
  type FieldErrors,
} from "./form-primitives";

const ARRANGEMENTS = ["onsite", "hybrid", "remote"] as const;

/**
 * What the user is looking for next (FR-004).
 *
 * Roles and locations are comma-separated in the interface and sent as lists,
 * which keeps a simple field for the user without losing the structure the API
 * stores.
 */
export function PreferenceForm({ initial }: { initial?: CareerPreference | null }) {
  const t = useTranslations("profile.preferences");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrors({});
    setSaved(false);

    const form = new FormData(event.currentTarget);
    const list = (value: FormDataEntryValue | null) =>
      String(value ?? "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

    const body = {
      desired_roles: list(form.get("desired_roles")),
      desired_locations: list(form.get("desired_locations")),
      working_arrangement: form.get("working_arrangement") || null,
      salary_min: form.get("salary_min") ? Number(form.get("salary_min")) : null,
      salary_max: form.get("salary_max") ? Number(form.get("salary_max")) : null,
      currency: form.get("currency") || null,
      source_language: form.get("source_language") ?? "en",
    };

    try {
      await api.putPreferences(body as CareerPreference);
      setSaved(true);
    } catch (error) {
      if (error instanceof ValidationError) setErrors(toFieldErrors(error.failures));
      else throw error;
    } finally {
      setPending(false);
    }
  }

  return (
    <Section title={t("title")}>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <Field
          label={t("desiredRoles")}
          name="desired_roles"
          errors={errors}
          hint={t("commaSeparated")}
        >
          <TextInput
            name="desired_roles"
            errors={errors}
            defaultValue={(initial?.desired_roles ?? []).join(", ")}
          />
        </Field>

        <Field
          label={t("desiredLocations")}
          name="desired_locations"
          errors={errors}
          hint={t("commaSeparated")}
        >
          <TextInput
            name="desired_locations"
            errors={errors}
            defaultValue={(initial?.desired_locations ?? []).join(", ")}
          />
        </Field>

        <Field label={t("workingArrangement")} name="working_arrangement" errors={errors}>
          <Select
            name="working_arrangement"
            errors={errors}
            defaultValue={initial?.working_arrangement ?? ""}
          >
            <option value="">—</option>
            {ARRANGEMENTS.map((value) => (
              <option key={value} value={value}>
                {t(`arrangements.${value}`)}
              </option>
            ))}
          </Select>
        </Field>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label={t("salaryMin")} name="salary_min" errors={errors}>
            <TextInput
              name="salary_min"
              type="number"
              min={0}
              errors={errors}
              defaultValue={initial?.salary_min ?? ""}
            />
          </Field>
          <Field label={t("salaryMax")} name="salary_max" errors={errors}>
            <TextInput
              name="salary_max"
              type="number"
              min={0}
              errors={errors}
              defaultValue={initial?.salary_max ?? ""}
            />
          </Field>
          <Field label={t("currency")} name="currency" errors={errors}>
            <TextInput
              name="currency"
              maxLength={3}
              errors={errors}
              defaultValue={initial?.currency ?? "JPY"}
            />
          </Field>
        </div>

        <div className="flex items-center gap-3">
          <SubmitButton pending={pending}>{t("save")}</SubmitButton>
          {saved && <span className="text-xs opacity-70">{t("saved")}</span>}
        </div>
      </form>
    </Section>
  );
}
