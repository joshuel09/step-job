"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, type CareerImport } from "@/lib/api";

/**
 * Following an import that was handed to the worker.
 *
 * A slow document does not hold the request open, so the interface has to say
 * what is happening and reach a definite answer either way (FR-005b). Polling
 * stops as soon as the import settles — a spinner that never resolves is the
 * failure this exists to avoid.
 */
const POLL_INTERVAL_MS = 1500;
const GIVE_UP_AFTER_MS = 5 * 60 * 1000;

export function ImportStatus({ initial }: { initial: CareerImport }) {
  const t = useTranslations("profile.import");
  const router = useRouter();
  const [record, setRecord] = useState(initial);
  const [gaveUp, setGaveUp] = useState(false);

  const settled = record.status === "completed" || record.status === "failed";

  useEffect(() => {
    if (settled) return;

    const startedAt = Date.now();
    let cancelled = false;

    const timer = setInterval(async () => {
      if (Date.now() - startedAt > GIVE_UP_AFTER_MS) {
        // Stop asking rather than poll for ever. The import itself is
        // unaffected — it is still running, and the page will show its result
        // when reloaded.
        setGaveUp(true);
        clearInterval(timer);
        return;
      }

      try {
        const latest = await api.getImport(record.id!);
        if (cancelled) return;

        setRecord(latest);
        if (latest.status === "completed" || latest.status === "failed") {
          clearInterval(timer);
          router.refresh();
        }
      } catch {
        // A transient failure to poll is not a failure of the import.
      }
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [record.id, settled, router]);

  async function onCancel() {
    try {
      setRecord(await api.cancelImport(record.id!));
    } catch {
      // Already finished. The next poll shows the real outcome.
    }
  }

  if (record.status === "failed") {
    return (
      <div role="alert" className="mt-4 rounded border border-amber-400 p-3 text-sm">
        <p className="font-medium">
          {t(`failures.${record.failure_reason ?? "extraction_failed"}`)}
        </p>
      </div>
    );
  }

  if (record.status === "completed") {
    return (
      <p className="mt-4 text-sm" aria-live="polite">
        {t("found", { count: record.entry_count })}
      </p>
    );
  }

  return (
    <div className="mt-4 flex items-center gap-3 text-sm" aria-live="polite">
      <span>{gaveUp ? t("stillRunning") : t("reading")}</span>
      {!gaveUp && (
        <button type="button" onClick={onCancel} className="text-xs underline opacity-70">
          {t("cancel")}
        </button>
      )}
    </div>
  );
}
