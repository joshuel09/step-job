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
      <p className="mb-3 text-sm opacity-80">{t("pasteExplanation")}</p>
      {/* Said up front, because a user with a 職務経歴書 needs to know their
          document will be read rather than flattened into English. */}
      <p className="mb-3 text-xs opacity-70">{t("japaneseNote")}</p>

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
          <p role="alert" className="text-xs text-red-600 dark:text-red-400">
            {errors.text}
          </p>
        )}
        <SubmitButton pending={pending}>{pending ? t("reading") : t("read")}</SubmitButton>
      </form>

      <hr className="my-5 border-neutral-200 dark:border-neutral-800" />

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
      <p className="text-xs opacity-70">{t("uploadExplanation")}</p>

      <label className="flex flex-col gap-1">
        <span className="sr-only">{t("uploadTitle")}</span>
        <input
          type="file"
          accept={ACCEPTED}
          disabled={pending}
          onChange={onChange}
          className="text-sm file:mr-3 file:rounded file:border file:border-neutral-300 file:bg-transparent file:px-3 file:py-1.5 file:text-sm dark:file:border-neutral-700"
        />
      </label>

      {pending && <p className="text-xs opacity-70">{t("reading")}</p>}
      {error && (
        <p role="alert" className="text-xs text-red-600 dark:text-red-400">
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
      <div role="alert" className="mt-4 rounded border border-amber-400 p-3 text-sm">
        {/* The reason matters: an unavailable service is worth returning to,
            an unreadable document never will be. */}
        <p className="font-medium">{t(`failures.${result.failure_reason ?? "extraction_failed"}`)}</p>
        {result.outcome?.message && <p className="mt-1 opacity-80">{result.outcome.message}</p>}
      </div>
    );
  }

  return (
    <div className="mt-4 rounded border border-neutral-200 p-3 text-sm dark:border-neutral-800">
      <p className="font-medium">{t("found", { count: result.entry_count })}</p>
      {result.outcome?.message && <p className="mt-1 text-xs opacity-80">{result.outcome.message}</p>}
      {result.outcome?.not_found?.length ? (
        <p className="mt-2 text-xs opacity-70">
          {t("notFound", { kinds: result.outcome.not_found.join(", ") })}
        </p>
      ) : null}
      <p className="mt-2 text-xs opacity-70">{t("nothingAddedYet")}</p>
    </div>
  );
}
