"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { currentUserId, isUserId } from "@/lib/dev-session";
import { api } from "@/lib/api";

import { Section } from "./form-primitives";

const RECEIPT_KEY = "step-job:profile-deletion:";
type DeletionReceipt = Awaited<ReturnType<typeof api.deleteProfile>>;
type StorageProblem = "unavailable" | "save" | "clear";

/** Bind the local reminder to its owner without storing the bearer UUID. */
async function receiptKey(): Promise<string | null> {
  const userId = await currentUserId();
  if (!isUserId(userId)) return null;
  // Keep the bearer UUID out of localStorage while binding the receipt to its owner.
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(userId));
  const owner = Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
  return `${RECEIPT_KEY}${owner}`;
}

/** Reject damaged or expired reminders before showing a restore action. */
function parseReceipt(value: string): DeletionReceipt | null {
  try {
    const receipt = JSON.parse(value) as DeletionReceipt;
    return Array.isArray(receipt.erased_immediately) &&
      typeof receipt.recoverable_until === "string" &&
      Date.parse(receipt.recoverable_until) > Date.now()
      ? receipt
      : null;
  } catch {
    return null;
  }
}

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
  const [receipt, setReceipt] = useState<DeletionReceipt | null>(null);
  const [pending, setPending] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [storageProblem, setStorageProblem] = useState<StorageProblem | null>(null);
  const [restoreError, setRestoreError] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const key = await receiptKey();
        if (!key) return;
        const saved = localStorage.getItem(key);
        if (!saved) return;
        const recovered = parseReceipt(saved);
        if (recovered) {
          if (active) setReceipt(recovered);
        } else localStorage.removeItem(key);
      } catch {
        if (active) setStorageProblem("unavailable");
      } finally {
        if (active) setLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

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

  /** Keep the API receipt in browser storage so reload does not hide Restore. */
  async function onDelete() {
    setPending(true);
    try {
      const deleted = await api.deleteProfile();
      setReceipt(deleted);
      setConfirming(false);
      try {
        const key = await receiptKey();
        if (!key) throw new Error("No browser session");
        localStorage.setItem(key, JSON.stringify(deleted));
        setStorageProblem(null);
      } catch {
        setStorageProblem("save");
      }
    } finally {
      setPending(false);
    }
  }

  /** Restore server data first, then remove the local reminder. */
  async function onRestore() {
    setPending(true);
    setRestoreError(false);
    try {
      await api.restoreProfile();
      setReceipt(null);
      try {
        const key = await receiptKey();
        if (key) localStorage.removeItem(key);
        setStorageProblem(null);
      } catch {
        setStorageProblem("clear");
      }
    } catch {
      setRestoreError(true);
    } finally {
      setPending(false);
    }
  }

  const storageWarning =
    storageProblem === "unavailable"
      ? t("recoveryStorageUnavailable")
      : storageProblem === "save"
        ? t("recoveryStorageSave")
        : storageProblem === "clear"
          ? t("recoveryStorageClear")
          : null;

  if (!loaded) {
    return (
      <Section title={t("title")}>
        <p role="status" className="text-sm">
          {t("checkingRecovery")}
        </p>
      </Section>
    );
  }

  if (receipt) {
    return (
      <Section title={t("deleted")}>
        <p className="text-sm">{t("deletedExplanation")}</p>
        <p className="hint mt-2">{t("recoveryDeviceLimit")}</p>
        <p className="mt-2 text-sm">
          {t("recoverableUntil", { date: new Date(receipt.recoverable_until).toLocaleString() })}
        </p>
        <p className="explain mt-2">
          {t("erasedNow", { fields: receipt.erased_immediately.join(", ") })}
        </p>
        {storageWarning && (
          <p role="alert" className="field-error">
            {storageWarning}
          </p>
        )}
        {restoreError && (
          <p role="alert" className="field-error">
            {t("restoreFailed")}
          </p>
        )}
        <button type="button" onClick={onRestore} disabled={pending} className="btn-form mt-4">
          {t("restore")}
        </button>
      </Section>
    );
  }

  return (
    <>
      {storageWarning && (
        <p role="alert" className="field-error">
          {storageWarning}
        </p>
      )}
      <Section title={t("exportTitle")}>
        <p className="explain">{t("exportExplanation")}</p>
        <button type="button" onClick={onExport} disabled={pending} className="btn-quiet mt-3">
          {t("export")}
        </button>
      </Section>

      <Section title={t("deleteTitle")}>
        {!confirming ? (
          <>
            <p className="explain">{t("deleteExplanation")}</p>
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="btn-quiet mt-3 text-brand-800"
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
              <button type="button" onClick={onDelete} disabled={pending} className="btn-danger">
                {t("confirmDelete")}
              </button>
              <button type="button" onClick={() => setConfirming(false)} className="btn-quiet">
                {t("cancel")}
              </button>
            </div>
          </div>
        )}
      </Section>
    </>
  );
}
