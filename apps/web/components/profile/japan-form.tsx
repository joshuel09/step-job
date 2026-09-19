"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { api, ValidationError, type JapanProfile } from "@/lib/api";

import { Field, Section, SubmitButton, TextInput, toFieldErrors, type FieldErrors } from "./form-primitives";

/**
 * Japan-specific circumstances.
 *
 * Every field is optional, and each carries its own disclosure control that is
 * off by default (FR-006). These are the fields that carry discrimination risk,
 * so the interface says plainly that nothing here reaches a generated document
 * unless the user opts it in — the closed default is the point, not a detail.
 */
const FIELDS = [
  { name: "residence_status", disclose: "disclose_residence_status", type: "text" },
  { name: "nationality", disclose: "disclose_nationality", type: "text" },
  { name: "visa_type", disclose: "disclose_visa", type: "text" },
  { name: "visa_expires_on", disclose: "disclose_visa", type: "date" },
  { name: "japanese_qualification", disclose: "disclose_japanese_qualification", type: "text" },
] as const;

export function JapanForm({ initial }: { initial?: JapanProfile | null }) {
  const t = useTranslations("profile.japan");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrors({});
    setSaved(false);

    const form = new FormData(event.currentTarget);
    const body: Record<string, unknown> = {};
    for (const [key, value] of form.entries()) {
      body[key] = value === "" ? null : value;
    }
    // Unchecked boxes are absent from FormData; absent must mean withheld.
    for (const flag of [
      "disclose_residence_status",
      "disclose_nationality",
      "disclose_visa",
      "disclose_work_authorisation",
      "disclose_japanese_qualification",
    ]) {
      body[flag] = form.get(flag) === "on";
    }
    body.work_authorisation = form.get("work_authorisation") === "on";

    try {
      await api.putJapan(body as JapanProfile);
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
      <p className="mb-3 text-xs opacity-70">{t("privacyNote")}</p>

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        {FIELDS.map(({ name, disclose, type }) => (
          <div key={name} className="flex flex-col gap-1">
            <Field label={t(name)} name={name} errors={errors}>
              <TextInput
                name={name}
                type={type}
                errors={errors}
                defaultValue={(initial?.[name] as string | undefined) ?? ""}
              />
            </Field>
            <label className="flex items-center gap-2 text-xs opacity-80">
              <input
                type="checkbox"
                name={disclose}
                defaultChecked={Boolean(initial?.[disclose as keyof JapanProfile])}
              />
              {t("includeInDocuments")}
            </label>
          </div>
        ))}

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            name="work_authorisation"
            defaultChecked={Boolean(initial?.work_authorisation)}
          />
          {t("work_authorisation")}
        </label>
        <label className="flex items-center gap-2 text-xs opacity-80">
          <input
            type="checkbox"
            name="disclose_work_authorisation"
            defaultChecked={Boolean(initial?.disclose_work_authorisation)}
          />
          {t("includeInDocuments")}
        </label>

        <div className="flex items-center gap-3">
          <SubmitButton pending={pending}>{t("save")}</SubmitButton>
          {saved && <span className="text-xs opacity-70">{t("saved")}</span>}
        </div>
      </form>
    </Section>
  );
}
