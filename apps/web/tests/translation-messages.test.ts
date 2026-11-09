import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import { describe, expect, it } from "vitest";

import en from "../messages/en.json";
import ja from "../messages/ja.json";
import { TRANSLATION_FIELDS, TRANSLATION_NOTICES } from "../lib/translation-labels";

const here = dirname(fileURLToPath(import.meta.url));
const schema = ts.createSourceFile(
  "schema-005.ts",
  readFileSync(join(here, "../../../packages/api-client/src/schema-005.ts"), "utf8"),
  ts.ScriptTarget.Latest,
  true,
);
const entryTypes: string[] = [];
/** Derive the API's runtime label obligations from its generated union. */
function visit(node: ts.Node) {
  if (
    ts.isPropertySignature(node) &&
    node.name.getText(schema) === "TranslatableEntry" &&
    node.type &&
    ts.isUnionTypeNode(node.type)
  ) {
    for (const member of node.type.types) {
      if (ts.isLiteralTypeNode(member) && ts.isStringLiteral(member.literal))
        entryTypes.push(member.literal.text);
    }
  }
  ts.forEachChild(node, visit);
}
visit(schema);

/** Resolve dotted computed keys independently of the rendering code. */
function lookup(catalogue: unknown, path: string): unknown {
  return path
    .split(".")
    .reduce<unknown>((value, key) => (value as Record<string, unknown>)?.[key], catalogue);
}

describe("computed translation review messages", () => {
  it("actually discovers API entry types and field labels", () => {
    expect(entryTypes).toContain("work_experience");
    expect(entryTypes).toContain("career_story");
    expect(Object.values(TRANSLATION_FIELDS).length).toBeGreaterThan(0);
  });
  it.each(["en", "ja"] as const)("has every field, entry type and notice in %s", (locale) => {
    const messages = locale === "en" ? en.profile.translations : ja.profile.translations;
    const keys = [
      ...[...Object.values(TRANSLATION_FIELDS), "other"].map((key) => `fields.${key}`),
      ...entryTypes.map((key) => `entryTypes.${key}`),
      ...TRANSLATION_NOTICES,
    ];
    expect(keys.filter((key) => typeof lookup(messages, key) !== "string")).toEqual([]);
  });
});
