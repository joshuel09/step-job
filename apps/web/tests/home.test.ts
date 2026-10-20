import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import en from "../messages/en.json";
import ja from "../messages/ja.json";
import { GLYPHS } from "../components/brand/icons";
import { AVAILABLE, HOTSPOTS, PLANNED, STEPS } from "../lib/site";

/**
 * The landing page is the only page that describes the product rather than
 * showing it, which makes it the one place a claim can be wrong without
 * anything failing. Two ways that happens, both checked here.
 *
 * `messages.test.ts` already holds the two catalogues to each other. This
 * holds them to what the page actually reads: a key the page asks for and no
 * catalogue defines renders as the key itself, in both languages, and the
 * parity test passes because neither has it.
 */

const here = dirname(fileURLToPath(import.meta.url));
const pages = join(here, "..", "app", "[locale]");

function message(catalogue: unknown, path: string): unknown {
  return path
    .split(".")
    .reduce<unknown>((node, key) => (node as Record<string, unknown>)?.[key], catalogue);
}

describe("the landing page", () => {
  it.each(AVAILABLE)("offers $key, which is a page that exists", ({ href }) => {
    expect(existsSync(join(pages, href, "page.tsx"))).toBe(true);
  });

  it.each(AVAILABLE)("draws a glyph for $key", ({ key }) => {
    expect(typeof GLYPHS[key]).toBe("function");
  });

  it.each(HOTSPOTS.filter((h) => h.href))("puts $key on a page that exists", ({ href }) => {
    expect(existsSync(join(pages, href as string, "page.tsx"))).toBe(true);
  });

  it.each(["en", "ja"] as const)("writes every marker's card in %s", (locale) => {
    const catalogue = locale === "en" ? en : ja;
    const required = ["visit", ...HOTSPOTS.flatMap(({ key }) => [`${key}.title`, `${key}.body`])];

    const missing = required.filter(
      (path) => typeof message((catalogue as Record<string, unknown>).world, path) !== "string",
    );
    expect(missing).toEqual([]);
  });

  it("never offers something that is only specified", () => {
    const offered = AVAILABLE.map(({ key }) => key) as readonly string[];
    expect(offered.filter((key) => (PLANNED as readonly string[]).includes(key))).toEqual([]);
  });

  it.each(["en", "ja"] as const)("says every one of its own words in %s", (locale) => {
    const catalogue = locale === "en" ? en : ja;
    const required = [
      "nav",
      "brandline",
      "headline",
      "lead",
      "start",
      "generate",
      "howTitle",
      "availableTitle",
      "plannedTitle",
      "plannedBody",
      "truthTitle",
      "truthBody",
      "makersTitle",
      "since",
      "makers.cat",
      ...["josh", "mich"].flatMap((who) => [`makers.${who}.name`, `makers.${who}.role`]),
      ...STEPS.flatMap((step) => [`steps.${step}.title`, `steps.${step}.body`]),
      ...AVAILABLE.flatMap(({ key }) => [`available.${key}.title`, `available.${key}.body`]),
      ...PLANNED.map((key) => `planned.${key}`),
    ];

    const missing = required.filter((path) => typeof message(catalogue.home, path) !== "string");
    expect(missing).toEqual([]);
  });
});
