#!/usr/bin/env node
/**
 * Fails the build when a translation is missing.
 *
 * FR-022 requires that a user who selects Japanese can complete every task with
 * no untranslated interface text. A missing key renders as the key itself —
 * visible to the user, invisible in code review — so it is caught here instead.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const load = (locale) =>
  JSON.parse(readFileSync(join(here, "..", "messages", `${locale}.json`), "utf8"));

function keyPaths(value, prefix = "") {
  if (value === null || typeof value !== "object") return [prefix];
  return Object.entries(value).flatMap(([key, child]) =>
    keyPaths(child, prefix ? `${prefix}.${key}` : key),
  );
}

const en = load("en");
const reference = new Set(keyPaths(en));
let failed = false;

for (const locale of ["ja"]) {
  const messages = load(locale);
  const present = new Set(keyPaths(messages));

  const missing = [...reference].filter((k) => !present.has(k)).sort();
  const extra = [...present].filter((k) => !reference.has(k)).sort();
  const empty = [...present]
    .filter((k) => {
      const value = k.split(".").reduce((node, part) => node?.[part], messages);
      return typeof value === "string" && value.trim() === "";
    })
    .sort();

  for (const [label, list] of [
    ["missing", missing],
    ["not present in en", extra],
    ["empty", empty],
  ]) {
    if (list.length) {
      failed = true;
      console.error(`${locale}: ${list.length} ${label}`);
      for (const key of list) console.error(`  ${key}`);
    }
  }

  if (!missing.length && !extra.length && !empty.length) {
    console.log(`${locale}: ${present.size} keys, complete`);
  }
}

if (failed) {
  console.error("\nTranslations are incomplete. Every key in en.json must exist and be non-empty.");
  process.exit(1);
}
