import { describe, expect, it } from "vitest";

import en from "../messages/en.json";
import ja from "../messages/ja.json";

/**
 * FR-022: a user who selects Japanese must be able to complete every task with
 * no untranslated interface text. A missing key renders as the key itself, so
 * this guards the requirement at the point where it is cheap to catch.
 */
function keyPaths(value: unknown, prefix = ""): string[] {
  if (value === null || typeof value !== "object") return [prefix];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
    keyPaths(child, prefix ? `${prefix}.${key}` : key),
  );
}

describe("message catalogues", () => {
  it("define the same keys in English and Japanese", () => {
    const enKeys = keyPaths(en).sort();
    const jaKeys = keyPaths(ja).sort();

    expect(jaKeys).toEqual(enKeys);
  });

  it("leave no Japanese value empty", () => {
    const empties = keyPaths(ja).filter((path) => {
      const value = path
        .split(".")
        .reduce<unknown>((node, key) => (node as Record<string, unknown>)?.[key], ja);
      return typeof value === "string" && value.trim() === "";
    });

    expect(empties).toEqual([]);
  });
});
