"use client";

import type { ReactNode } from "react";

/**
 * Field-level error display.
 *
 * FR-014 requires a rejection name the offending field and explain why. The API
 * returns `{field, reason}` pairs; these helpers carry that through to the field
 * the user actually needs to fix, rather than collapsing it into "save failed".
 */
export type FieldErrors = Record<string, string>;

export function toFieldErrors(failures: { field: string; reason: string }[]): FieldErrors {
  return Object.fromEntries(failures.map(({ field, reason }) => [field, reason]));
}

export function Field({
  label,
  name,
  errors,
  hint,
  children,
}: {
  label: string;
  name: string;
  errors?: FieldErrors;
  hint?: string;
  children: ReactNode;
}) {
  const error = errors?.[name];
  const errorId = `${name}-error`;

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-sm font-medium">
        {label}
      </label>
      {children}
      {hint && !error && <p className="text-xs opacity-70">{hint}</p>}
      {error && (
        <p id={errorId} role="alert" className="text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}

export function TextInput({
  name,
  errors,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { name: string; errors?: FieldErrors }) {
  const invalid = Boolean(errors?.[name]);
  return (
    <input
      id={name}
      name={name}
      aria-invalid={invalid || undefined}
      aria-describedby={invalid ? `${name}-error` : undefined}
      className={`rounded border px-3 py-2 text-sm ${
        invalid ? "border-red-500" : "border-neutral-300 dark:border-neutral-700"
      } bg-transparent`}
      {...props}
    />
  );
}

export function TextArea({
  name,
  errors,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { name: string; errors?: FieldErrors }) {
  const invalid = Boolean(errors?.[name]);
  return (
    <textarea
      id={name}
      name={name}
      rows={4}
      aria-invalid={invalid || undefined}
      aria-describedby={invalid ? `${name}-error` : undefined}
      className={`rounded border px-3 py-2 text-sm ${
        invalid ? "border-red-500" : "border-neutral-300 dark:border-neutral-700"
      } bg-transparent`}
      {...props}
    />
  );
}

export function Select({
  name,
  errors,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & { name: string; errors?: FieldErrors }) {
  const invalid = Boolean(errors?.[name]);
  return (
    <select
      id={name}
      name={name}
      aria-invalid={invalid || undefined}
      className={`rounded border px-3 py-2 text-sm ${
        invalid ? "border-red-500" : "border-neutral-300 dark:border-neutral-700"
      } bg-transparent`}
      {...props}
    >
      {children}
    </select>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
      <h2 className="mb-3 text-lg font-semibold">{title}</h2>
      {children}
    </section>
  );
}

export function SubmitButton({ children, pending }: { children: ReactNode; pending?: boolean }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
    >
      {children}
    </button>
  );
}
