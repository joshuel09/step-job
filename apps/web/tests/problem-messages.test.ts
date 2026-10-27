import { describe, expect, it } from "vitest";

import { problemMessage } from "../components/profile/form-primitives";
import { ApiError } from "../lib/api";
import en from "../messages/en.json";
import ja from "../messages/ja.json";

/**
 * A form that fails must say so (#154).
 *
 * Before this, every rejection the API did not name a field for was rethrown:
 * the button did nothing, no message appeared, and the user could not tell
 * whether their work had been saved. The rule now is that a failure either
 * reaches its field or reaches this message.
 *
 * `messages-usage.test.ts` cannot see these keys — they are asked for through
 * a translator passed as an argument, not a literal namespace — so they are
 * checked here instead, in both languages, which is what #126 was about.
 */

const KEYS = ["unreachable", "unknown"] as const;

describe("the message for a failure with no field", () => {
  it("says the connection failed when the API could not be reached", () => {
    // `fetch` rejects with a TypeError when it never reached the host.
    expect(problemMessage(new TypeError("Failed to fetch"), (key) => key)).toBe(
      "problems.unreachable",
    );
  });

  it("falls back to the general message for a rejection from the API", () => {
    expect(problemMessage(new ApiError(404, "not_found", "No profile found"), (key) => key)).toBe(
      "problems.unknown",
    );
  });

  it("handles something thrown that is not an Error at all", () => {
    expect(problemMessage("boom", (key) => key)).toBe("problems.unknown");
  });

  it.each(KEYS)("has a '%s' message in both languages", (key) => {
    for (const [language, catalogue] of [
      ["en", en],
      ["ja", ja],
    ] as const) {
      const message = catalogue.common.problems[key];
      expect(message, `${language} is missing common.problems.${key}`).toBeTruthy();
      expect(typeof message).toBe("string");
    }
  });

  it("never promises the change was kept", () => {
    // Principle IV: the one thing the user needs from a failure is to know
    // that nothing was stored, so they do not walk away believing it was.
    expect(en.common.problems.unreachable).toContain("Nothing was changed");
    expect(en.common.problems.unknown).toContain("nothing was changed");
    expect(ja.common.problems.unreachable).toContain("保存されていません");
    expect(ja.common.problems.unknown).toContain("保存されていません");
  });
});
