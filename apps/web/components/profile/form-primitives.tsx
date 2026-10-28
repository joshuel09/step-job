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
      <label htmlFor={name} className="field-label">
        {label}
      </label>
      {children}
      {hint && !error && <p className="hint">{hint}</p>}
      {error && (
        <p id={errorId} role="alert" className="field-error">
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
}: React.InputHTMLAttributes<HTMLInputElement> & {
  name: string;
  errors?: FieldErrors;
}) {
  const invalid = Boolean(errors?.[name]);
  return (
    <input
      id={name}
      name={name}
      aria-invalid={invalid || undefined}
      aria-describedby={invalid ? `${name}-error` : undefined}
      className="field"
      {...props}
    />
  );
}

export function TextArea({
  name,
  errors,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  name: string;
  errors?: FieldErrors;
}) {
  const invalid = Boolean(errors?.[name]);
  return (
    <textarea
      id={name}
      name={name}
      rows={4}
      aria-invalid={invalid || undefined}
      aria-describedby={invalid ? `${name}-error` : undefined}
      className="field"
      {...props}
    />
  );
}

export function Select({
  name,
  errors,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & {
  name: string;
  errors?: FieldErrors;
}) {
  const invalid = Boolean(errors?.[name]);
  return (
    <select id={name} name={name} aria-invalid={invalid || undefined} className="field" {...props}>
      {children}
    </select>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="surface">
      <h2 className="surface-title">{title}</h2>
      {children}
    </section>
  );
}

export function SubmitButton({ children, pending }: { children: ReactNode; pending?: boolean }) {
  return (
    <button type="submit" disabled={pending} className="btn-form self-start">
      {children}
    </button>
  );
}

/**
 * A failure that belongs to no particular field.
 *
 * A form whose button does nothing is the worst of both worlds: the user
 * cannot tell whether their work was saved. Every rejection the API names a
 * field for goes to that field; everything else — the server unreachable, a
 * profile that is being erased, a fault we did not foresee — says so here,
 * and says plainly that nothing was stored (Principle IV).
 *
 * The API's own message is not shown. It is written in English, and FR-022
 * requires a Japanese user meet no untranslated interface text.
 */
export function problemMessage(error: unknown, t: (key: string) => string): string {
  // `fetch` rejects with a TypeError when it cannot reach the host at all.
  return error instanceof TypeError ? t("problems.unreachable") : t("problems.unknown");
}

export function Problem({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="problem">
      {message}
    </p>
  );
}
