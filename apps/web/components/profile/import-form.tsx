"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ApiError, ValidationError, type CareerImport } from "@/lib/api";

import { ImportStatus } from "./import-status";

import { Section, SubmitButton, TextArea, toFieldErrors, type FieldErrors } from "./form-primitives";

/**
 * Starting an import from pasted text.
 *
 * The copy is deliberate about what happens next: nothing joins the profile
 * here. Everything extracted waits in review, and the user decides. Saying so
 * before they paste is better than surprising them afterwards.
 */
export function ImportForm({ onComplete }: { onComplete?: (result: CareerImport) => void }) {
  const t = useTranslations("profile.import");
  const router = useRouter();
  const [errors, setErrors] = useState<FieldErrors>({});
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<CareerImport | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setErrors({});
    setResult(null);

    const text = String(new FormData(event.currentTarget).get("text") ?? "");

    try {
      const imported = await api.importText(text);
      setResult(imported);
      onComplete?.(imported);
      router.refresh();
    } catch (error) {
      if (error instanceof ValidationError) setErrors(toFieldErrors(error.failures));
      else throw error;
    } finally {
      setPending(false);
    }
  }

  return (
    <Section title={t("pasteTitle")}>
      <p className="explain mb-3">{t("pasteExplanation")}</p>
      {/* Said up front, because a user with a 職務経歴書 needs to know their
          document will be read rather than flattened into English. */}
      <p className="hint mb-3">{t("japaneseNote")}</p>

      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <TextArea
          name="text"
          rows={10}
          errors={errors}
          required
          placeholder={t("pastePlaceholder")}
          aria-label={t("pasteTitle")}
        />
        {errors.text && (
          <p role="alert" className="field-error">
            {errors.text}
          </p>
        )}
        <SubmitButton pending={pending}>{pending ? t("reading") : t("read")}</SubmitButton>
      </form>

      <hr className="divider my-5" />

      <UploadField
        onResult={(imported) => {
          setResult(imported);
          onComplete?.(imported);
          router.refresh();
        }}
      />

      {/* A handed-off import is followed rather than reported once; an import
          that already finished is reported directly. */}
      {result &&
        (result.status === "running" || result.status === "pending" ? (
          <ImportStatus initial={result} />
        ) : (
          <ImportResult result={result} />
        ))}
    </Section>
  );
}

const ACCEPTED = ".pdf,.docx";

function UploadField({ onResult }: { onResult: (result: CareerImport) => void }) {
  const t = useTranslations("profile.import");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setPending(true);
    setError(null);
    try {
      onResult(await api.uploadImport(file));
    } catch (caught) {
      // 413 and 415 are refusals with a reason the user can act on, not faults.
      if (caught instanceof ApiError) setError(caught.message);
      else throw caught;
    } finally {
      setPending(false);
      event.target.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-medium">{t("uploadTitle")}</h3>
      {/* The accepted formats are stated before the user tries, per FR-003. */}
      <p className="hint">{t("uploadExplanation")}</p>

      <label className="flex flex-col gap-1">
        <span className="sr-only">{t("uploadTitle")}</span>
        <input
          type="file"
          accept={ACCEPTED}
          disabled={pending}
          onChange={onChange}
          className="text-sm text-ink-soft file:mr-3 file:rounded-lg file:border file:border-cream-300 file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-brand-700 hover:file:border-brand-200"
        />
      </label>

      {pending && <p className="hint">{t("reading")}</p>}
      {error && (
        <p role="alert" className="field-error">
          {error}
        </p>
      )}
    </div>
  );
}

function ImportResult({ result }: { result: CareerImport }) {
  const t = useTranslations("profile.import");

  if (result.status === "failed") {
    return (
      <div role="alert" className="notice mt-4">
        {/* The reason matters: an unavailable service is worth returning to,
            an unreadable document never will be. */}
        <p className="font-medium">{t(`failures.${result.failure_reason ?? "extraction_failed"}`)}</p>
        {result.outcome?.message && <p className="mt-1 text-ink-soft">{result.outcome.message}</p>}
      </div>
    );
  }

  return (
    <div className="entry mt-4">
      <p className="font-medium">{t("found", { count: result.entry_count })}</p>
      {result.outcome?.message && <p className="hint mt-1">{result.outcome.message}</p>}
      {result.outcome?.not_found?.length ? (
        <p className="hint mt-2">
          {t("notFound", { kinds: result.outcome.not_found.join(", ") })}
        </p>
      ) : null}
      <p className="hint mt-2">{t("nothingAddedYet")}</p>
    </div>
  );
}
