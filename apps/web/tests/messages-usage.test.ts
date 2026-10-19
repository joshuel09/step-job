import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import en from "../messages/en.json";
import ja from "../messages/ja.json";
import { PROFILE_LINKS } from "../lib/site";

/**
 * Every string the code asks for is a string the catalogues hold.
 *
 * `messages.test.ts` compares the two catalogues to each other, which cannot
 * see this: the profile menu asked for `profile.settings`, that key exists in
 * both languages as a *namespace*, and next-intl printed `profile.settings` on
 * screen for months (#126). Both catalogues agreed, and the user saw the key.
 *
 * So the check has to come from the other side — what is called, not what is
 * stored — and it has to insist on a string, because resolving to an object is
 * the failure.
 *
 * Only literal keys on translators with a literal namespace are checked. A
 * template namespace (`useTranslations(`profile.${section}`)`) or a computed
 * key cannot be resolved without running the page; `home.test.ts` covers the
 * computed ones on the landing page by listing them.
 */

const here = dirname(fileURLToPath(import.meta.url));
const roots = [join(here, "..", "app"), join(here, "..", "components")];

function sources(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sources(path);
    return entry.isFile() && path.endsWith(".tsx") ? [path] : [];
  });
}

/** `const t = useTranslations("profile")` → `t` resolves under `profile`. */
function bindings(source: string): Map<string, string> {
  const found = new Map<string, string>();
  const pattern =
    /(?:const|let)\s+(\w+)\s*=\s*(?:await\s+)?(?:useTranslations|getTranslations)\(\s*"([^"]+)"\s*\)/g;
  for (const [, name, namespace] of source.matchAll(pattern)) found.set(name, namespace);
  return found;
}

function lookup(catalogue: unknown, path: string): unknown {
  return path
    .split(".")
    .reduce<unknown>((node, key) => (node as Record<string, unknown>)?.[key], catalogue);
}

describe("the profile navigation", () => {
  it.each(["en", "ja"] as const)("labels every link with a string in %s", (locale) => {
    const catalogue = locale === "en" ? en : ja;

    const broken = PROFILE_LINKS.filter(
      ({ label }) => typeof lookup(catalogue, `profile.${label}`) !== "string",
    ).map(({ label }) => `profile.${label}`);

    expect(broken).toEqual([]);
  });
});

describe("every translated string the code asks for", () => {
  const calls = roots
    .flatMap(sources)
    .flatMap((file) => {
      const source = readFileSync(file, "utf8");
      const translators = bindings(source);
      if (translators.size === 0) return [];

      return [...source.matchAll(/\b(\w+)\(\s*"([^"${}]+)"\s*[,)]/g)].flatMap(([, name, key]) => {
        const namespace = translators.get(name);
        return namespace ? [{ file, path: `${namespace}.${key}` }] : [];
      });
    })
    .sort((a, b) => a.path.localeCompare(b.path));

  it("is actually being collected", () => {
    // A regex that quietly matches nothing would make everything below pass.
    expect(calls.length).toBeGreaterThan(50);
  });

  it.each(["en", "ja"] as const)("resolves to a string in %s", (locale) => {
    const catalogue = locale === "en" ? en : ja;

    const broken = calls
      .filter(({ path }) => typeof lookup(catalogue, path) !== "string")
      .map(({ path, file }) => `${path} (${file.split("/apps/web/")[1]})`);

    expect([...new Set(broken)]).toEqual([]);
  });
});
