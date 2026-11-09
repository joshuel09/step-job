import { describe, expect, it } from "vitest";
import { applyTranslationOption, containsTranslationOption } from "../lib/translation-options";

describe("choosing an English reading", () => {
  it("replaces the one identifiable reading without changing other words", () => {
    expect(
      applyTranslationOption("Manager in Tokyo", ["Manager", "Section Chief"], "Section Chief"),
    ).toBe("Section Chief in Tokyo");
  });
  it("does not guess which occurrence to change", () => {
    expect(
      applyTranslationOption(
        "Manager reports to Manager",
        ["Manager", "Section Chief"],
        "Section Chief",
      ),
    ).toBe("Manager reports to Manager");
  });
  it("leaves custom English alone when no option occurs", () => {
    expect(
      applyTranslationOption("Engineering lead", ["Manager", "Section Chief"], "Manager"),
    ).toBe("Engineering lead");
  });
  it("does not replace a reading inside a different word", () => {
    expect(
      applyTranslationOption("Managerial work", ["Manager", "Section Chief"], "Section Chief"),
    ).toBe("Managerial work");
  });
  it("uses the full reading when options overlap", () => {
    expect(applyTranslationOption("Section Chief", ["Chief", "Section Chief"], "Manager")).toBe(
      "Manager",
    );
  });
});

it("does not count a word fragment as the user's selected wording", () => {
  expect(containsTranslationOption("Managerial work", "Manager")).toBe(false);
  expect(containsTranslationOption("Manager in Tokyo", "Manager")).toBe(true);
  expect(containsTranslationOption("Text", "")).toBe(false);
});
