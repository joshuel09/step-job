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

/* --- the drawing's grid -------------------------------------------------
   The illustration is isometric: ground coordinates run -1..1 on each axis,
   u towards the lower right and v towards the lower left. These live here
   rather than in the component because the markers have to land on the same
   geometry the drawing is built from — typing the two sets of numbers
   separately is how a marker ends up floating beside its subject. */
export const WORLD_W = 1600;
export const WORLD_H = 800;
const OX = 800;
const OY = 520;
export const HX = 350;
export const HY = 115;
export const SLOPE = HY / HX;

export function gx(u: number, v: number) {
  return OX + (u - v) * HX;
}

export function gy(u: number, v: number) {
  return OY + (u + v) * HY;
}

/** A box on the plate: its footprint, how tall it is, and how far it is lifted. */
export type Solid = { u: number; v: number; du: number; dv: number; h: number; base?: number };

/** The Step Job building, and the sign standing on its roof. */
export const BUILDING: Solid = { u: 0.3, v: -0.42, du: 0.3, dv: 0.26, h: 270 };
export const ROOF_SIGN: Solid = { u: 0.3, v: -0.42, du: 0.17, dv: 0.14, h: 58, base: 270 };

/** The laptop on the table, and the lid standing on its back edge. */
export const LAPTOP: Solid = { u: 0.82, v: 0.52, du: 0.075, dv: 0.05, h: 4, base: 40 };
export const LID = { w: 2 * LAPTOP.du * HX, lean: 7, h: 30 };

/**
 * The middle of the laptop's screen. The lid is a parallelogram standing on
 * the base's back edge: along the edge, then up and a little back.
 */
export function lidCentre() {
  const x = gx(LAPTOP.u - LAPTOP.du, LAPTOP.v - LAPTOP.dv);
  const y = gy(LAPTOP.u - LAPTOP.du, LAPTOP.v - LAPTOP.dv) - (LAPTOP.base ?? 0) - LAPTOP.h;
  return { x: x + LID.w / 2 + LID.lean / 2, y: y + (LID.w * SLOPE) / 2 - LID.h / 2 };
}

/**
 * A point on a solid's lower-left face, given in that face's own flat
 * coordinates: x across it from the top-left corner, y straight down it.
 */
export function onFace({ u, v, du, dv, h, base = 0 }: Solid, x: number, y: number) {
  return {
    x: gx(u - du, v + dv) + x,
    y: gy(u - du, v + dv) - base - h + x * SLOPE + y,
  };
}

/**
 * The points on the drawing you can press. `side` and `up` say which way the
 * card opens, so a marker near an edge does not open off the page.
 */
export const HOTSPOTS = [
  { key: "sign", ...onFace(ROOF_SIGN, 60, 28), href: undefined, side: "right", up: false },
  {
    key: "rirekisho",
    ...onFace(BUILDING, 180, 59),
    href: "profile/documents/rirekisho",
    side: "left",
    up: false,
  },
  { key: "import", ...onFace(BUILDING, 180, 139), href: "profile/import", side: "left", up: false },
  { key: "profile", ...onFace(BUILDING, 180, 219), href: "profile", side: "left", up: true },
  {
    key: "stories",
    x: gx(0.86, 0.06) + 42,
    y: gy(0.86, 0.06) - 74,
    href: "profile/stories",
    side: "left",
    up: true,
  },
  { key: "makers", ...lidCentre(), href: undefined, side: "left", up: true },
] as const;

export type HotspotKey = (typeof HOTSPOTS)[number]["key"];
