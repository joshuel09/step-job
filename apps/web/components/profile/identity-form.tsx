"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { api, ValidationError, type Identity } from "@/lib/api";

import { Field, Section, SubmitButton, TextInput, toFieldErrors, type FieldErrors } from "./form-primitives";

export function IdentityForm({ initial }: { initial?: Identity | null }) {
  const t = useTranslations("profile.identity");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrors({});
    setSaved(false);

    const form = new FormData(event.currentTarget);
    const body = Object.fromEntries(
      [...form.entries()].map(([k, v]) => [k, v === "" ? null : v]),
    ) as unknown as Identity;

    try {
      await api.putIdentity(body);
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
        <Field label={t("fullNameLatin")} name="full_name_latin" errors={errors}>
          <TextInput
            name="full_name_latin"
            errors={errors}
            required
            defaultValue={initial?.full_name_latin ?? ""}
          />
        </Field>

        {/* A single name string: a one-part name, or one that does not split
            into given and family, must be valid. */}
        <Field label={t("fullNameJapanese")} name="full_name_japanese" errors={errors}>
          <TextInput
            name="full_name_japanese"
            errors={errors}
            defaultValue={initial?.full_name_japanese ?? ""}
          />
        </Field>

        <Field label={t("furigana")} name="furigana" errors={errors} hint={t("furiganaHint")}>
          <TextInput name="furigana" errors={errors} defaultValue={initial?.furigana ?? ""} />
        </Field>

        <Field label={t("email")} name="email" errors={errors}>
          <TextInput name="email" type="email" errors={errors} defaultValue={initial?.email ?? ""} />
        </Field>

        <Field label={t("phone")} name="phone" errors={errors}>
          <TextInput name="phone" errors={errors} defaultValue={initial?.phone ?? ""} />
        </Field>

        <div className="flex items-center gap-3">
          <SubmitButton pending={pending}>{t("save")}</SubmitButton>
          {saved && <span className="text-xs opacity-70">{t("saved")}</span>}
        </div>
      </form>
    </Section>
  );
}
