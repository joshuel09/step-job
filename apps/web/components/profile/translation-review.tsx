"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useId, useState, useTransition } from "react";

import {
  api,
  ApiError,
  ValidationError,
  type ResumeReadinessReport,
  type StoredTranslation,
  type TranslationDraft,
  type TranslationDraftRequest,
  type UntranslatedName,
} from "@/lib/api";
import { applyTranslationOption, containsTranslationOption } from "@/lib/translation-options";

import { TRANSLATION_FIELDS, type TranslationNotice } from "@/lib/translation-labels";

import { Problem, problemMessage } from "./form-primitives";

/** Compare one source with editable English; only an explicit approval writes. */
function TranslationRow({
  subject,
  source,
  label,
  stored,
  onChange,
}: {
  subject: TranslationDraftRequest;
  source: string | null;
  label: string;
  stored?: StoredTranslation;
  onChange: (message: Exclude<TranslationNotice, "nameSaved">) => void;
}) {
  const t = useTranslations("profile.translations");
  const tc = useTranslations("common");
  const id = useId();
  const [text, setText] = useState(stored?.text ?? "");
  const [currentSource, setCurrentSource] = useState(source);
  const [draft, setDraft] = useState<TranslationDraft | null>(null);
  const [draftUsed, setDraftUsed] = useState(false);
  const [choices, setChoices] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [settled, setSettled] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const alternativesResolved = (draft?.alternatives ?? []).every((alternative, index) => {
    const choice = choices[index];
    return (
      choice === "own" ||
      (choice !== undefined &&
        choice !== "" &&
        containsTranslationOption(text, alternative.options[Number(choice)] ?? ""))
    );
  });

  /** Keep existing English on failure, and freeze editing while a draft is in flight. */
  async function makeDraft() {
    setBusy(true);
    setProblem(null);
    try {
      const next = await api.draftTranslation(subject);
      setCurrentSource(next.source_text);
      setDraft(next);
      setDraftUsed(false);
      setChoices({});
    } catch (error) {
      if (error instanceof ApiError && error.status === 503) setProblem(t("unavailable"));
      else if (error instanceof ApiError && error.status === 502) setProblem(t("unusable"));
      else if (error instanceof ValidationError) setProblem(t("invalidSource"));
      else if (error instanceof ApiError && error.status === 404) setProblem(t("entryMissing"));
      else setProblem(problemMessage(error, tc));
    } finally {
      setBusy(false);
    }
  }

  /** Submit the user's exact text, or remove only the selected stored approval. */
  async function saveOrRemove(remove = false) {
    setBusy(true);
    setProblem(null);
    try {
      if (remove && stored) await api.deleteTranslation(stored.id);
      else await api.approveTranslation({ ...subject, text });
      setSettled(true);
      onChange(remove ? "removed" : "saved");
    } catch (error) {
      if (error instanceof ValidationError) setProblem(t("invalidApproval"));
      else if (error instanceof ApiError && error.status === 404) setProblem(t("entryMissing"));
      else setProblem(problemMessage(error, tc));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="surface flex flex-col gap-4" aria-labelledby={`${id}-title`}>
      <div>
        <h3 id={`${id}-title`} className="font-semibold">
          {label}
        </h3>
        <p className="hint">{t(`fields.${TRANSLATION_FIELDS[subject.field] ?? "other"}`)}</p>
        {stored && <p className="notice mt-2">{t("staleNote")}</p>}
      </div>
      <div className="grid min-w-0 gap-4 md:grid-cols-2">
        <div className="min-w-0">
          <h4 className="field-label">{t("source")}</h4>
          <p className="entry mt-1 whitespace-pre-wrap break-words" lang="ja">
            {currentSource ?? t("sourceMissing")}
          </p>
        </div>
        <div className="min-w-0">
          {draft && (
            <div className="entry mb-4 flex flex-col gap-2">
              <h4 className="field-label">{t("suggestion")}</h4>
              <p className="whitespace-pre-wrap break-words" lang="en">
                {draft.text}
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-form"
                  disabled={busy || settled || draftUsed}
                  onClick={() => {
                    setText(draft.text);
                    setChoices({});
                    setDraftUsed(true);
                  }}
                >
                  {t("useSuggestion")}
                </button>
                <button
                  type="button"
                  className="btn-quiet"
                  disabled={busy || settled}
                  onClick={() => {
                    setDraft(null);
                    setChoices({});
                    setDraftUsed(false);
                  }}
                >
                  {t("discardSuggestion")}
                </button>
              </div>
            </div>
          )}
          <label htmlFor={`${id}-english`} className="field-label">
            {t("english")}
          </label>
          <textarea
            id={`${id}-english`}
            className="field mt-1"
            rows={5}
            lang="en"
            value={text}
            disabled={busy || settled}
            onChange={(event) => setText(event.target.value)}
          />
          <p className="hint mt-1">{t("exactWords")}</p>
        </div>
      </div>
      {draft && <p className="notice">{t("draftOnly")}</p>}
      {draft && draft.alternatives.length > 0 && (
        <div className="flex flex-col gap-3">
          <p className="explain">{t("alternativesHint")}</p>
          {draft.alternatives.map((alternative, index) => (
            <fieldset
              key={index}
              className="entry flex flex-col gap-2"
              disabled={busy || settled || !draftUsed}
            >
              <legend className="px-1 font-medium" lang="ja">
                {alternative.phrase}
              </legend>
              {alternative.note && <p className="hint">{alternative.note}</p>}
              <label className="field-label" htmlFor={`${id}-choice-${index}`}>
                {t("chooseMeaning")}
              </label>
              <select
                id={`${id}-choice-${index}`}
                className="field"
                value={choices[index] ?? ""}
                onChange={(event) => {
                  const choice = event.target.value;
                  setChoices((previous) => ({ ...previous, [index]: choice }));
                  const option = alternative.options[Number(choice)];
                  if (choice !== "" && choice !== "own" && option) {
                    setText((previous) =>
                      applyTranslationOption(previous, alternative.options, option),
                    );
                  }
                }}
              >
                <option value="">{t("choosePlaceholder")}</option>
                {alternative.options.map((option, optionIndex) => (
                  <option key={optionIndex} value={String(optionIndex)}>
                    {option}
                  </option>
                ))}
                <option value="own">{t("ownWording")}</option>
              </select>
            </fieldset>
          ))}
          {!alternativesResolved && <p className="hint">{t("resolveAlternatives")}</p>}
        </div>
      )}
      <Problem message={problem} />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="btn-quiet"
          disabled={busy || settled || currentSource === null}
          onClick={makeDraft}
        >
          {busy ? t("working") : t("draft")}
        </button>
        <button
          type="button"
          className="btn-form"
          disabled={
            busy ||
            settled ||
            currentSource === null ||
            !text.trim() ||
            !alternativesResolved ||
            (draft !== null && !draftUsed)
          }
          onClick={() => saveOrRemove()}
        >
          {t("approve")}
        </button>
        {stored && (
          <button
            type="button"
            className="btn-quiet"
            disabled={busy || settled}
            onClick={() => saveOrRemove(true)}
          >
            {t("remove")}
          </button>
        )}
      </div>
      <p className="hint">{t("replaceDraft")}</p>
    </article>
  );
}

const NAME_TARGETS: Record<string, { section: string; field: string }> = {
  "work_experience.employer_name": { section: "experiences", field: "employer_name_english" },
  "education.institution": { section: "education", field: "institution_english" },
  "certification.name": { section: "certifications", field: "name_english" },
  "certification.issuer": { section: "certifications", field: "issuer_english" },
};

/** Official names are profile facts supplied by the user, never model drafts. */
function EnglishNameRow({ entry, onSaved }: { entry: UntranslatedName; onSaved: () => void }) {
  const t = useTranslations("profile.translations");
  const tc = useTranslations("common");
  const id = useId();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const target = NAME_TARGETS[`${entry.entry_type}.${entry.field}`];

  /** Patch the existing entry route so the profile stays the single source. */
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!target) {
      setProblem(t("nameUnsupported"));
      return;
    }
    setBusy(true);
    setProblem(null);
    try {
      await api.updateEntry(target.section, entry.entry_id, { [target.field]: text });
      setSaved(true);
      onSaved();
    } catch (error) {
      if (error instanceof ValidationError) setProblem(t("invalidName"));
      else setProblem(problemMessage(error, tc));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={save} className="entry flex flex-col gap-3">
      <p className="font-medium" lang="ja">
        {entry.recorded_name}
      </p>
      {target ? (
        <>
          <label htmlFor={`${id}-name`} className="field-label">
            {t("officialName")}
          </label>
          <input
            id={`${id}-name`}
            className="field"
            value={text}
            lang="en"
            disabled={busy || saved}
            onChange={(event) => setText(event.target.value)}
          />
          <button
            type="submit"
            className="btn-form self-start"
            disabled={busy || saved || !text.trim()}
          >
            {t("saveName")}
          </button>
        </>
      ) : (
        <p className="hint">{t("nameUnsupported")}</p>
      )}
      <Problem message={problem} />
    </form>
  );
}

/** Separate missing English, stale approvals and supplied names into distinct worklists. */
export function TranslationReview({
  report,
  failure,
  locale,
}: {
  report: ResumeReadinessReport | null;
  failure: "missing" | "unavailable" | null;
  locale: string;
}) {
  const t = useTranslations("profile.translations");
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(null);
  const [refreshing, startRefresh] = useTransition();
  const refresh = () => startRefresh(() => router.refresh());
  const changed = (message: TranslationNotice) => {
    setNotice(t(message));
    refresh();
  };
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <Link href={`/${locale}/profile/documents/resume`} className="link">
          {t("toResume")}
        </Link>
        <button type="button" className="btn-quiet" disabled={refreshing} onClick={refresh}>
          {t("reload")}
        </button>
      </div>
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      {failure && (
        <section className="surface">
          <p role="alert">{failure === "missing" ? t("noProfile") : t("loadFailed")}</p>
          <Link className="link" href={`/${locale}/profile`}>
            {t("back")}
          </Link>
        </section>
      )}
      {report && (
        <>
          {!report.can_generate && <p className="notice">{t("missingRequired")}</p>}
          <section className="flex flex-col gap-4" aria-label={t("needsTitle")}>
            <h2 className="surface-title">{t("needsTitle")}</h2>
            {report.needs_english.length === 0 && <p className="explain">{t("nothingMissing")}</p>}
            {report.needs_english.map((entry) => (
              <TranslationRow
                key={`missing:${entry.entry_type}:${entry.entry_id}:${entry.field}:${entry.source_text}`}
                subject={{
                  entry_type: entry.entry_type,
                  entry_id: entry.entry_id,
                  field: entry.field,
                }}
                source={entry.source_text}
                label={entry.label}
                onChange={changed}
              />
            ))}
          </section>
          {report.stale_translations.length > 0 && (
            <section className="flex flex-col gap-4" aria-label={t("staleTitle")}>
              <h2 className="surface-title">{t("staleTitle")}</h2>
              {report.stale_translations.map((entry) => (
                <TranslationRow
                  key={`stale:${entry.id}:${entry.source_text}:${entry.approved_at}`}
                  subject={{
                    entry_type: entry.entry_type,
                    entry_id: entry.entry_id,
                    field: entry.field,
                  }}
                  source={entry.source_text ?? null}
                  label={t(`entryTypes.${entry.entry_type}`)}
                  stored={entry}
                  onChange={changed}
                />
              ))}
            </section>
          )}
          {report.untranslated_names.length > 0 && (
            <section className="surface flex flex-col gap-4" aria-label={t("namesTitle")}>
              <h2 className="surface-title">{t("namesTitle")}</h2>
              <p className="explain">{t("namesNote")}</p>
              {report.untranslated_names.map((entry) => (
                <EnglishNameRow
                  key={`${entry.entry_type}:${entry.entry_id}:${entry.field}`}
                  entry={entry}
                  onSaved={() => changed("nameSaved")}
                />
              ))}
            </section>
          )}
        </>
      )}
    </>
  );
}
