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

/** The key of a card the page offers. */
export type AvailableKey = (typeof AVAILABLE)[number]["key"];

/** Specified, not built. Named on the page, never linked. */
export const PLANNED = ["shokumu", "resume"] as const;

/** The three steps the page explains, in order. */
export const STEPS = ["capture", "import", "generate"] as const;

/**
 * The navigation bar under /profile. `label` is a key in the `profile`
 * namespace, and it must resolve to a string: `settings` is that page's own
 * namespace, and asking for a namespace prints the key path on screen (#126).
 */
export const PROFILE_LINKS = [
  { href: "", label: "title" },
  { href: "/stories", label: "storiesNav" },
  { href: "/import", label: "importNav" },
  { href: "/review", label: "reviewNav" },
  { href: "/documents/rirekisho", label: "rirekishoNav" },
  { href: "/settings", label: "settings.title" },
] as const;
