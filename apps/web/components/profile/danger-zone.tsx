"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { api } from "@/lib/api";

import { Section } from "./form-primitives";

/**
 * Export and deletion.
 *
 * FR-026 requires the user be told, before deletion proceeds, which data is
 * erased immediately, which is recoverable, and when the window closes. So this
 * is a two-step flow: the consequences are stated first, and the destructive
 * call only happens after the user confirms against them.
 */
export function DangerZone() {
  const t = useTranslations("profile.settings");
  const [confirming, setConfirming] = useState(false);
  const [receipt, setReceipt] = useState<{
    erased_immediately: string[];
    recoverable_until: string;
  } | null>(null);
  const [pending, setPending] = useState(false);

  async function onExport() {
    setPending(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/profile/export`,
        { method: "POST", credentials: "include" },
      );
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "step-job-profile.zip";
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setPending(false);
    }
  }

  async function onDelete() {
    setPending(true);
    try {
      setReceipt(await api.deleteProfile());
      setConfirming(false);
    } finally {
      setPending(false);
    }
  }

  async function onRestore() {
    setPending(true);
    try {
      await api.restoreProfile();
      setReceipt(null);
    } finally {
      setPending(false);
    }
  }

  if (receipt) {
    return (
      <Section title={t("deleted")}>
        <p className="text-sm">{t("deletedExplanation")}</p>
        <p className="mt-2 text-sm">
          {t("recoverableUntil", { date: new Date(receipt.recoverable_until).toLocaleString() })}
        </p>
        <p className="mt-2 text-sm opacity-70">
          {t("erasedNow", { fields: receipt.erased_immediately.join(", ") })}
        </p>
        <button
          type="button"
          onClick={onRestore}
          disabled={pending}
          className="mt-4 rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
        >
          {t("restore")}
        </button>
      </Section>
    );
  }

  return (
    <>
      <Section title={t("exportTitle")}>
        <p className="text-sm opacity-80">{t("exportExplanation")}</p>
        <button
          type="button"
          onClick={onExport}
          disabled={pending}
          className="mt-3 rounded border border-neutral-300 px-4 py-2 text-sm disabled:opacity-50 dark:border-neutral-700"
        >
          {t("export")}
        </button>
      </Section>

      <Section title={t("deleteTitle")}>
        {!confirming ? (
          <>
            <p className="text-sm opacity-80">{t("deleteExplanation")}</p>
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="mt-3 rounded border border-red-500 px-4 py-2 text-sm text-red-600 dark:text-red-400"
            >
              {t("delete")}
            </button>
          </>
        ) : (
          <div role="alert" className="flex flex-col gap-3">
            {/* Stated before the call, not after: the user decides against the
                actual consequences. */}
            <p className="text-sm font-medium">{t("confirmHeading")}</p>
            <ul className="list-disc pl-5 text-sm">
              <li>{t("confirmImmediate")}</li>
              <li>{t("confirmRecoverable")}</li>
              <li>{t("confirmPermanent")}</li>
            </ul>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onDelete}
                disabled={pending}
                className="rounded bg-red-600 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                {t("confirmDelete")}
              </button>
              <button
                type="button"
                onClick={() => setConfirming(false)}
                className="rounded border border-neutral-300 px-4 py-2 text-sm dark:border-neutral-700"
              >
                {t("cancel")}
              </button>
            </div>
          </div>
        )}
      </Section>
    </>
  );
}
