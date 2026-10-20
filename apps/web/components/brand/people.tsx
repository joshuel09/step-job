/**
 * The two of us, and the cat, from the 2018 About screen.
 *
 * The originals were detailed stock-style characters. These keep what made
 * each one recognisable — Josh's round glasses and red tie, Mich's bob and
 * her jacket's white buttons, the tabby's stripes — and drop everything else,
 * because a flat shape scales and a drawing of a face does not.
 *
 * Skin and hair are the one place the brand palette does not reach. Tinting a
 * person blue to match a design system is how an illustration stops looking
 * like a person.
 */

const SKIN = "#f3c9a6";
const HAIR = "#241c18";
const SUIT = "#1c2530";
const SHIRT = "#ffffff";
const TIE = "#c6392f";
// The cat's own colours. A silver Persian is grey through brown, not orange.
const COAT = "#9a9084";
const COAT_LIGHT = "#b9b1a5";
const COAT_DARK = "#6b6257";
const CREAM = "#e9e2d6";
const EYE = "#8aa36a";
const NOSE = "#d79ea0";

/** A portrait disc. The figure is clipped to it, so shoulders end at the edge. */
function Disc({
  id,
  children,
  className,
}: {
  id: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <svg viewBox="0 0 96 96" role="presentation" aria-hidden className={className}>
      <defs>
        <clipPath id={id}>
          <circle cx="48" cy="48" r="48" />
        </clipPath>
      </defs>
      <circle cx="48" cy="48" r="48" fill="#e0f2fe" />
      <g clipPath={`url(#${id})`}>{children}</g>
    </svg>
  );
}

/** Programming and design. Glasses and the red tie. */
export function Josh({ className }: { className?: string }) {
  return (
    <Disc id="disc-josh" className={className}>
      {/* Shoulders, cropped by the disc. */}
      <path d="M14 96c0-15 15-24 34-24s34 9 34 24z" fill={SUIT} />
      <path d="M40 74l8 10 8-10-8-4z" fill={SHIRT} />
      <path d="M46 82h4l3 14h-10z" fill={TIE} />
      {/* Head. */}
      <ellipse cx="48" cy="46" rx="19" ry="21" fill={SKIN} />
      {/* Hair: a cap with a side part, as the original had. */}
      <path d="M29 44c0-13 8-21 19-21s19 8 19 21c0-7-7-10-14-10-9 0-14 4-17 10z" fill={HAIR} />
      {/* The glasses that made the character his. */}
      <g fill="none" stroke={HAIR} strokeWidth="2.4">
        <circle cx="40" cy="47" r="7" />
        <circle cx="56" cy="47" r="7" />
        <path d="M47 47h2M29 45l4 1M67 45l-4 1" />
      </g>
    </Disc>
  );
}

/** Design and programming. The bob and the buttoned jacket. */
export function Mich({ className }: { className?: string }) {
  return (
    <Disc id="disc-mich" className={className}>
      <path d="M14 96c0-15 15-24 34-24s34 9 34 24z" fill={SUIT} />
      <circle cx="48" cy="84" r="2.6" fill={SHIRT} />
      <circle cx="48" cy="93" r="2.6" fill={SHIRT} />
      <path d="M41 73l7 9 7-9z" fill={SHIRT} />
      <ellipse cx="48" cy="46" rx="19" ry="21" fill={SKIN} />
      {/* Bob: a fringe across the forehead and length down both sides. */}
      <path
        d="M27 48c0-15 9-24 21-24s21 9 21 24v14c0-6-2-9-5-10V38c-5 4-10 6-16 6s-11-2-16-6v24c-3 1-5 4-5 10z"
        fill="#3b2a24"
      />
    </Disc>
  );
}

/**
 * A fur outline: an ellipse whose edge is made of tufts rather than a curve.
 *
 * A Persian drawn with ellipses reads as a cat wearing a collar — the ruff
 * becomes a hard ring. Pushing the midpoint of each segment out by a varying
 * amount turns the same shape into something that ends in fur. The jitter is
 * a fixed function of the index, not random, so the drawing is identical on
 * the server and in the browser.
 */
function fur(
  cx: number,
  cy: number,
  rx: number,
  ry: number,
  tufts: number,
  amp: number,
  seed = 1,
): string {
  const at = (angle: number, scale = 1) =>
    [cx + Math.cos(angle) * rx * scale, cy + Math.sin(angle) * ry * scale] as const;

  // A deterministic wobble in [0.6, 1.4], so the tufts are uneven the way fur is.
  const wobble = (i: number) => 1 + 0.4 * Math.sin(i * 2.399 + seed * 1.7) * Math.cos(i * 1.117);

  const step = (Math.PI * 2) / tufts;
  const [sx, sy] = at(0);
  const parts = [`M${sx.toFixed(1)} ${sy.toFixed(1)}`];
  for (let i = 0; i < tufts; i += 1) {
    const mid = at(step * (i + 0.5), 1 + amp * wobble(i));
    const end = at(step * (i + 1));
    parts.push(
      `Q${mid[0].toFixed(1)} ${mid[1].toFixed(1)} ${end[0].toFixed(1)} ${end[1].toFixed(1)}`,
    );
  }
  return `${parts.join("")}Z`;
}

/**
 * The cat's shapes, so the desk scene and the credits place the same one.
 *
 * Drawn from the photograph: a Persian, so a broad flat face, small ears set
 * low and wide, a short muzzle, and the expression that comes with it. The
 * coat is silver tabby — grey-brown with darker markings, cream through the
 * chest and chin.
 *
 * Every outline is a fur edge rather than an ellipse, and the ruff is three
 * of them stacked, because on a cat this fluffy the silhouette is most of
 * what makes her her.
 */
export function CatShapes() {
  return (
    <>
      {/* The tail: a plume curling up the side, three tufted blobs rather
          than one, so it tapers. */}
      <g className="cat-tail">
        <path d={fur(12, 40, 8, 7, 11, 0.2, 4)} fill={COAT} />
        <path d={fur(8, 32, 6, 7, 10, 0.22, 7)} fill={COAT} />
        <path d={fur(8, 25, 4.5, 5, 9, 0.24, 12)} fill={COAT_LIGHT} />
      </g>

      {/* The body, loafed. Two layers: the coat, and a lighter chest. */}
      <path d={fur(32, 37, 23, 13, 16, 0.14, 2)} fill={COAT} />
      <path d={fur(32, 40, 13, 9, 12, 0.18, 9)} fill={CREAM} opacity="0.5" />

      {/* The ruff: three fur edges, widest at the back, so the neck reads as
          depth rather than as a ring. */}
      <path d={fur(32, 26, 21, 17, 20, 0.13, 3)} fill={COAT_LIGHT} />
      <path d={fur(32, 26, 19, 15, 18, 0.14, 5)} fill={CREAM} />
      <path d={fur(32, 29, 14, 11, 14, 0.16, 6)} fill={CREAM} />

      {/* Ears: small, low, wide apart, each with a tuft inside. */}
      <path d="M19.5 13.5l-1.5-6 8 2.5z" fill={COAT} />
      <path d="M48.5 13.5l1.5-6-8 2.5z" fill={COAT} />
      <path d="M20.6 11.8l-.7-3 3.2 1.1z" fill={CREAM} />
      <path d="M47.4 11.8l.7-3-3.2 1.1z" fill={CREAM} />

      {/* The head: broad and round, with the coat breaking over the top. */}
      <path d={fur(32, 21, 16, 14, 16, 0.08, 8)} fill={COAT} />

      {/* Tabby markings over the forehead. */}
      <g fill={COAT_DARK}>
        <path d="M32 8c1 0 1.6.6 1.6 1.4L32 15l-1.6-5.6C30.4 8.6 31 8 32 8z" />
        <path d="M25 9.6c.9-.3 1.7.1 2 .9L28 16l-3.6-4.6c-.5-.7-.3-1.5.6-1.8z" />
        <path d="M39 9.6c-.9-.3-1.7.1-2 .9L36 16l3.6-4.6c.5-.7.3-1.5-.6-1.8z" />
      </g>

      {/* Cheeks and muzzle: short, which is the whole face. */}
      <path d={fur(32, 27, 11, 7, 12, 0.12, 11)} fill={CREAM} />
      <ellipse cx="27.5" cy="27.5" rx="5" ry="4" fill={CREAM} />
      <ellipse cx="36.5" cy="27.5" rx="5" ry="4" fill={CREAM} />

      {/* Eyes: half-lidded, with the lid level across the top rather than
          slanting towards the nose. The slant was a scowl; a flat heavy lid
          is boredom, which is the look she actually has. The left one sits a
          fraction lower, because a face that is exactly symmetrical reads as
          posed. */}
      <g>
        <ellipse cx="25.6" cy="20.6" rx="3.6" ry="2.9" fill={EYE} />
        <ellipse cx="38.4" cy="20.6" rx="3.6" ry="2.9" fill={EYE} />
        <ellipse cx="25.8" cy="21.2" rx="1.2" ry="1.7" fill={HAIR} />
        <ellipse cx="38.2" cy="21.2" rx="1.2" ry="1.7" fill={HAIR} />
        <path className="cat-lid" d="M21.9 19.9h7.4v-2.3h-7.4z" fill={COAT} />
        <path className="cat-lid" d="M34.7 19.6h7.4v-2.3h-7.4z" fill={COAT} />
      </g>

      {/* Nose and the mouth that makes the expression. */}
      <path d="M32 24.6l-2.2-2h4.4z" fill={NOSE} />
      {/* The mouth: nearly flat, with the corners a hair below the middle.
          A deep frown is a complaint; this is a cat who has considered you
          and decided not to comment. */}
      <path
        d="M32 26.6v1.3M28.8 29.3c1.1-.9 2.2-.9 3.2-.3 1-.6 2.1-.6 3.2.3"
        fill="none"
        stroke={COAT_DARK}
        strokeWidth="1.1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Fur over the top of the ruff, so the chest is not one flat shape. */}
      <g stroke={COAT_LIGHT} strokeWidth="0.9" strokeLinecap="round" fill="none" opacity="0.8">
        <path d="M21 31c-1.5 2-2 4-1.6 6M26 34c-1 2.2-1.2 4.4-.6 6.4M38 34c1 2.2 1.2 4.4.6 6.4M43 31c1.5 2 2 4 1.6 6" />
      </g>

      {/* Whiskers, carried past the ruff. Stopping inside it made them read
          as scratches across the fur rather than as whiskers. They disappear
          below about 40px, which is correct: at that size they are noise. */}
      <g stroke="#ffffff" strokeWidth="0.6" strokeLinecap="round" opacity="0.85">
        <path d="M23 26.4l-15-3.4M23 28.2l-15 1.6M41 26.4l15-3.4M41 28.2l15 1.6" />
      </g>
    </>
  );
}

/** On the desk in 2018, saying Meoow. Still here. */
export function Cat({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 48" role="presentation" aria-hidden className={className}>
      <CatShapes />
    </svg>
  );
}
