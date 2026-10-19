/**
 * What the landing page is allowed to say the product does.
 *
 * Here rather than in the page so a test can hold it to two things that are
 * easy to get wrong and invisible once wrong: that every route offered is a
 * page that exists, and that nothing specified-but-unbuilt is offered as
 * though it worked. A landing page that links to a document the product
 * cannot produce makes the same kind of untrue claim Principle IV forbids a
 * generated document.
 */

/** A working page. `href` is relative to the locale segment. */
export const AVAILABLE = [
  { key: "profile", href: "profile" },
  { key: "import", href: "profile/import" },
  { key: "rirekisho", href: "profile/documents/rirekisho" },
  { key: "stories", href: "profile/stories" },
] as const;

/** Specified, not built. Named on the page, never linked. */
export const PLANNED = ["shokumu", "resume"] as const;

/** The three steps the page explains, in order. */
export const STEPS = ["capture", "import", "generate"] as const;
