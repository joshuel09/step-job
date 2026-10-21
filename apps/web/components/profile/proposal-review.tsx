"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, type ProposedEntry, type WorkExperience } from "@/lib/api";

/**
 * Reviewing what an outside source suggested.
 *
 * Every proposal is editable before it is accepted, because the version the
 * user approves is the version the profile keeps (FR-019). Where a possible
 * duplicate was found, merging is offered — but so is keeping both, because a
 * flagged duplicate is a suggestion and the user may know better (FR-034).
 */
export function ProposalReview({
  proposals,
  experiences,
}: {
  proposals: ProposedEntry[];
  experiences: WorkExperience[];
}) {
  const t = useTranslations("profile.review");
  const router = useRouter();
  const [editing, setEditing] = useState<Record<string, Record<string, string>>>({});
  const [pending, setPending] = useState<string | null>(null);

  function edit(id: string, field: string, value: string) {
    setEditing((current) => ({ ...current, [id]: { ...(current[id] ?? {}), [field]: value } }));
  }

  async function act(id: string, action: () => Promise<unknown>) {
    setPending(id);
    try {
      await action();
      router.refresh();
    } finally {
      setPending(null);
    }
  }

  if (proposals.length === 0) {
    return <p className="explain">{t("empty")}</p>;
  }

  return (
    <ul className="flex flex-col gap-4">
      {proposals.map((proposal) => {
        const payload = proposal.payload as Record<string, string>;
        const corrections = editing[proposal.id!] ?? {};
        const duplicate = experiences.find((e) => e.id === proposal.possible_duplicate_of);
        const evidence = proposal.evidence as Record<string, { quote: string }> | null;
        const conflicts = (proposal.conflicts ?? []) as { fields?: string[]; reason: string }[];
        const busy = pending === proposal.id;

        return (
          <li
            key={proposal.id}
            className="surface"
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <span className="text-xs uppercase tracking-wide text-ink-faint">
                {t(`types.${proposal.entry_type}`)}
              </span>
              <span className="hint">{t("from", { source: proposal.source })}</span>
            </div>

            {duplicate && (
              <p
                role="status"
                className="mb-3 rounded-lg border border-brand-200 bg-brand-50 p-2 text-xs text-brand-800"
              >
                {t("possibleDuplicate", {
                  role: `${duplicate.job_title} — ${duplicate.employer_name}`,
                })}
              </p>
            )}

            {conflicts.length > 0 && (
              <ul
                role="alert"
                className="mb-3 rounded-lg border border-brand-200 bg-brand-50 p-2 text-xs text-brand-800"
              >
                {/* Flagged, not resolved. The document disagrees with itself and
                    the user knows which reading is right (FR-012a). */}
                {conflicts.map((conflict, index) => (
                  <li key={index}>{t("conflict", { reason: conflict.reason })}</li>
                ))}
              </ul>
            )}

            <div className="flex flex-col gap-2">
              {Object.entries(payload).map(([field, value]) => {
                const quote = evidence?.[field]?.quote;
                const conflicted = conflicts.some((c) => c.fields?.includes(field));

                return (
                  <label key={field} className="flex flex-col gap-1">
                    <span className="text-xs font-medium text-ink-soft">{field}</span>
                    <input
                      defaultValue={String(value ?? "")}
                      onChange={(event) => edit(proposal.id!, field, event.target.value)}
                      aria-invalid={conflicted || undefined}
                      className="field px-2 py-1"
                    />
                    {/* The passage this value was taken from. A user should be
                        able to see a value was read rather than guessed — which
                        is the whole reason the extraction records it. */}
                    {quote && (
                      <span className="hint italic">
                        {t("fromSource")}: “{quote}”
                      </span>
                    )}
                  </label>
                );
              })}
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  act(proposal.id!, () =>
                    api.acceptProposal(
                      proposal.id!,
                      Object.keys(corrections).length ? corrections : undefined,
                    ),
                  )
                }
                className="btn-form py-1.5"
              >
                {duplicate ? t("keepBoth") : t("accept")}
              </button>

              {duplicate && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    act(proposal.id!, () =>
                      api.mergeProposal(
                        proposal.id!,
                        duplicate.id!,
                        Object.keys(corrections).length ? corrections : undefined,
                      ),
                    )
                  }
                  className="btn-quiet px-3 py-1.5"
                >
                  {t("merge")}
                </button>
              )}

              <button
                type="button"
                disabled={busy}
                onClick={() => act(proposal.id!, () => api.rejectProposal(proposal.id!))}
                className="btn-quiet px-3 py-1.5"
              >
                {t("reject")}
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
