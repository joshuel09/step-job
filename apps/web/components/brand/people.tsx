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
 * The cat's shapes, so the desk scene and the credits place the same one.
 *
 * Drawn from the photograph rather than from the 2018 artwork: a Persian, so
 * a broad flat face, small ears set low and wide, the ruff around the neck,
 * a short muzzle and the expression that comes with it. The coat is silver
 * tabby — grey-brown with darker markings, cream through the chest and chin.
 */
export function CatShapes() {
  return (
    <>
      {/* The tail, a plume rather than a line. */}
      <path
        d="M12 44c-6-1-9-5-8-10 1-4 4-6 7-5"
        fill="none"
        stroke={COAT}
        strokeWidth="7"
        strokeLinecap="round"
      />
      <path
        d="M12 44c-5-1-7-4-6-8"
        fill="none"
        stroke={COAT_LIGHT}
        strokeWidth="2.6"
        strokeLinecap="round"
      />

      {/* Loafed: the body is a low mound with the coat breaking its outline. */}
      <path d="M10 46c0-10 5-17 13-19 6-1 14-1 20 0 8 2 13 9 13 19z" fill={COAT} />
      <path d="M22 46c0-7 4-12 10-12s10 5 10 12z" fill={CREAM} opacity="0.55" />

      {/* The ruff, behind the head and wider than it. */}
      <ellipse cx="34" cy="24" rx="19" ry="16" fill={CREAM} />
      <path
        d="M15 24c2-6 7-10 19-10s17 4 19 10c-3-2-6-1-8 1-3-3-7-4-11-4s-8 1-11 4c-2-2-5-3-8-1z"
        fill={COAT_LIGHT}
      />

      {/* Ears: small, low, wide apart, with a tuft inside each. */}
      <path d="M19.5 13.5l-1.5-6 8 2.5z" fill={COAT} />
      <path d="M48.5 13.5l1.5-6-8 2.5z" fill={COAT} />
      <path d="M20.6 11.8l-.7-3 3.2 1.1z" fill={CREAM} />
      <path d="M47.4 11.8l.7-3-3.2 1.1z" fill={CREAM} />

      {/* The head: round and broad, not a wedge. */}
      <ellipse cx="34" cy="21" rx="16" ry="14" fill={COAT} />
      {/* Tabby markings over the forehead. */}
      <g fill={COAT_DARK}>
        <path d="M34 8c1 0 1.6.6 1.6 1.4L34 15l-1.6-5.6C32.4 8.6 33 8 34 8z" />
        <path d="M27 9.6c.9-.3 1.7.1 2 .9L30 16l-3.6-4.6c-.5-.7-.3-1.5.6-1.8z" />
        <path d="M41 9.6c-.9-.3-1.7.1-2 .9L38 16l3.6-4.6c.5-.7.3-1.5-.6-1.8z" />
      </g>

      {/* Cheeks and muzzle: short, which is the whole face. */}
      <ellipse cx="34" cy="27" rx="11" ry="7" fill={CREAM} />
      <ellipse cx="29.5" cy="27.5" rx="5" ry="4" fill={CREAM} />
      <ellipse cx="38.5" cy="27.5" rx="5" ry="4" fill={CREAM} />

      {/* Eyes: round and green, with the lid carried low. Half the expression
          is how much of them is covered. */}
      <g>
        <ellipse cx="27.6" cy="20.4" rx="3.3" ry="3.1" fill={EYE} />
        <ellipse cx="40.4" cy="20.4" rx="3.3" ry="3.1" fill={EYE} />
        <ellipse cx="27.6" cy="20.6" rx="1.3" ry="2.4" fill={HAIR} />
        <ellipse cx="40.4" cy="20.6" rx="1.3" ry="2.4" fill={HAIR} />
        {/* The lid, in coat colour, taking the top third of each eye. */}
        <path
          d="M24.3 19.4c1-1.6 5.6-1.6 6.6 0l.4-2.6h-7.4zM37.1 19.4c1-1.6 5.6-1.6 6.6 0l.4-2.6h-7.4z"
          fill={COAT}
        />
      </g>

      {/* Nose and the mouth that makes the expression. */}
      <path d="M34 24.6l-2.2-2h4.4z" fill={NOSE} />
      <path
        d="M34 26.6v1.6M34 28.2c-1.4 1.6-3.4 1.6-4.6.2M34 28.2c1.4 1.6 3.4 1.6 4.6.2"
        fill="none"
        stroke={COAT_DARK}
        strokeWidth="1.1"
        strokeLinecap="round"
      />
      {/* Whiskers. They disappear below about 40px, which is correct: at that
          size they would only be noise. */}
      <g stroke={CREAM} strokeWidth="0.7" strokeLinecap="round" opacity="0.9">
        <path d="M24 26.5l-7-2M24 28.2l-7 1M44 26.5l7-2M44 28.2l7 1" />
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
