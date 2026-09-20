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
    return <p className="text-sm opacity-70">{t("empty")}</p>;
  }

  return (
    <ul className="flex flex-col gap-4">
      {proposals.map((proposal) => {
        const payload = proposal.payload as Record<string, string>;
        const corrections = editing[proposal.id!] ?? {};
        const duplicate = experiences.find((e) => e.id === proposal.possible_duplicate_of);
        const busy = pending === proposal.id;

        return (
          <li
            key={proposal.id}
            className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <span className="text-xs uppercase tracking-wide opacity-60">
                {t(`types.${proposal.entry_type}`)}
              </span>
              <span className="text-xs opacity-60">{t("from", { source: proposal.source })}</span>
            </div>

            {duplicate && (
              <p
                role="status"
                className="mb-3 rounded bg-amber-50 p-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300"
              >
                {t("possibleDuplicate", {
                  role: `${duplicate.job_title} — ${duplicate.employer_name}`,
                })}
              </p>
            )}

            <div className="flex flex-col gap-2">
              {Object.entries(payload).map(([field, value]) => (
                <label key={field} className="flex flex-col gap-1">
                  <span className="text-xs font-medium opacity-70">{field}</span>
                  <input
                    defaultValue={String(value ?? "")}
                    onChange={(event) => edit(proposal.id!, field, event.target.value)}
                    className="rounded border border-neutral-300 bg-transparent px-2 py-1 text-sm dark:border-neutral-700"
                  />
                </label>
              ))}
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
                className="rounded bg-neutral-900 px-3 py-1.5 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
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
                  className="rounded border border-neutral-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-neutral-700"
                >
                  {t("merge")}
                </button>
              )}

              <button
                type="button"
                disabled={busy}
                onClick={() => act(proposal.id!, () => api.rejectProposal(proposal.id!))}
                className="rounded border border-neutral-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-neutral-700"
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
