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
const TABBY = "#b4824e";
const TABBY_DARK = "#8a5f36";

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

/** The tabby's shapes, so the desk scene can place the same cat. */
export function CatShapes() {
  return (
    <>
      {/* Tail, curling up the way the original's did. */}
      <path
        d="M44 40c9 2 14-2 14-9 0-5-3-8-7-8"
        fill="none"
        stroke={TABBY}
        strokeWidth="5"
        strokeLinecap="round"
      />
      <path d="M18 44c0-12 5-19 13-19s13 7 13 19z" fill={TABBY} />
      <circle cx="31" cy="20" r="11" fill={TABBY} />
      <path d="M22 12l-1-9 8 5zM40 12l1-9-8 5z" fill={TABBY} />
      <g fill={TABBY_DARK}>
        <rect x="26" y="31" width="10" height="2.4" rx="1.2" />
        <rect x="26" y="36" width="10" height="2.4" rx="1.2" />
      </g>
      <g fill={HAIR}>
        <circle cx="27" cy="19" r="1.7" />
        <circle cx="35" cy="19" r="1.7" />
      </g>
      <path d="M31 23l-2.4-2h4.8z" fill={TIE} />
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
