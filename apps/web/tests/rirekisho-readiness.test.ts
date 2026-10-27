import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import en from "../messages/en.json";
import ja from "../messages/ja.json";

/**
 * The readiness report names fields; the page has to name them in Japanese.
 *
 * The API answers with its own field names — `identity.furigana`,
 * `certifications` — which are English identifiers, not something to show a
 * user (FR-022). The view translates them, and this holds the translation
 * table to what the API can actually send: the names are read out of
 * `readiness.py` rather than copied here, because a field added there and
 * forgotten here would reach the page as a raw identifier.
 *
 * `messages-usage.test.ts` cannot see these keys. They are asked for as
 * `t(`fields.${key}`)`, a computed key, which is exactly the case it says it
 * cannot resolve without running the page.
 */

const here = dirname(fileURLToPath(import.meta.url));
const readiness = readFileSync(
  join(here, "..", "..", "api", "app", "rirekisho", "readiness.py"),
  "utf8",
);
const view = readFileSync(
  join(here, "..", "components", "profile", "rirekisho-readiness.tsx"),
  "utf8",
);

/** The strings in a Python tuple literal assigned at the top level. */
function constant(name: string): string[] {
  const block = readiness.match(new RegExp(`^${name}\\s*=\\s*\\(([^)]*)\\)`, "m"));
  if (!block) throw new Error(`${name} is no longer a tuple literal in readiness.py`);

  const values = [...block[1].matchAll(/"([^"]+)"/g)].map(([, value]) => value);
  if (values.length === 0) throw new Error(`${name} parsed to nothing`);
  return values;
}

/** Every field name the report can put in `missing_required` or `missing_optional`. */
const FIELDS = [
  // `missing_required` is the whole identity when there is no identity at all.
  "identity",
  ...constant("REQUIRED").map((field) => `identity.${field}`),
  ...constant("OPTIONAL_IDENTITY").map((field) => `identity.${field}`),
  ...constant("OPTIONAL_SECTIONS"),
];

/** The kinds of entry `_english_entries` reports, as the contract enumerates them. */
const ENTRY_TYPES = ["work_experience", "education", "certification"];

/** The view's own table, read from its source: it is not importable here. */
const translated = new Map(
  [...view.matchAll(/^\s*"?([\w.]+)"?:\s*"(\w+)",$/gm)].map(([, field, key]) => [field, key]),
);

function message(catalogue: typeof en, path: string): unknown {
  return path
    .split(".")
    .reduce<unknown>((node, key) => (node as Record<string, unknown>)?.[key], catalogue);
}

describe("the readiness view", () => {
  it("reads the field names out of the API, not out of thin air", () => {
    expect(FIELDS).toContain("identity.full_name_latin");
    expect(FIELDS).toContain("certifications");
    expect(translated.size).toBeGreaterThan(0);
  });

  it.each(FIELDS)("has a label for %s", (field) => {
    expect(translated.get(field), `no label for ${field} in rirekisho-readiness.tsx`).toBeTruthy();
  });

  it.each(["en", "ja"] as const)("names every field in %s", (locale) => {
    const catalogue = locale === "en" ? en : ja;

    const untranslated = FIELDS.filter((field) => {
      const key = translated.get(field);
      return typeof message(catalogue, `profile.rirekisho.readiness.fields.${key}`) !== "string";
    });

    expect(untranslated).toEqual([]);
  });

  it.each(["en", "ja"] as const)("names every kind of entry in %s", (locale) => {
    const catalogue = locale === "en" ? en : ja;

    const untranslated = ENTRY_TYPES.filter(
      (kind) =>
        typeof message(catalogue, `profile.rirekisho.readiness.entryTypes.${kind}`) !== "string",
    );

    expect(untranslated).toEqual([]);
  });

  it("never says the missing entries were filled in", () => {
    // R-001: the user is told what has no Japanese version. Nothing is
    // written for them, and the page must not suggest otherwise.
    const { readiness: copy } = en.profile.rirekisho;
    expect(copy.englishExplanation).toContain("never translated");
    expect(copy.blankExplanation).toContain("Nothing is invented");
  });
});
