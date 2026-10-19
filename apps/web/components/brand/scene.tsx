import { CatShapes } from "@/components/brand/people";

/**
 * The 2018 home header, redrawn: a window onto the city, the STEP JOB
 * billboard on a rooftop, a desk with a laptop, someone working, the clock on
 * the wall and the cat sitting where it always sat.
 *
 * Flat and geometric rather than detailed. The original was a raster
 * illustration with shading and a dozen greys; this is a handful of shapes in
 * the brand palette plus the one warm colour the people need, so it recolours
 * with the theme and stays sharp at any size.
 */
export function DeskScene({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 320 260" role="presentation" aria-hidden className={className}>
      <defs>
        <linearGradient id="scene-sky" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#e0f2fe" />
          <stop offset="100%" stopColor="#bae6fd" />
        </linearGradient>
        <linearGradient id="scene-screen" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="100%" stopColor="#e0f2fe" />
        </linearGradient>
      </defs>

      {/* The room. */}
      <rect width="320" height="260" rx="28" fill="url(#scene-sky)" />

      {/* The window, and the city through it. */}
      <rect x="26" y="28" width="150" height="110" rx="10" fill="#ffffff" opacity="0.75" />
      <g fill="#7dd3fc">
        <rect x="38" y="86" width="26" height="44" rx="3" />
        <rect x="70" y="68" width="22" height="62" rx="3" />
        <rect x="98" y="96" width="24" height="34" rx="3" />
        <rect x="128" y="76" width="34" height="54" rx="3" />
      </g>
      <g fill="#ffffff" opacity="0.8">
        <rect x="44" y="94" width="5" height="6" rx="1" />
        <rect x="54" y="94" width="5" height="6" rx="1" />
        <rect x="44" y="106" width="5" height="6" rx="1" />
        <rect x="76" y="78" width="5" height="6" rx="1" />
        <rect x="76" y="92" width="5" height="6" rx="1" />
        <rect x="136" y="88" width="5" height="6" rx="1" />
        <rect x="148" y="88" width="5" height="6" rx="1" />
        <rect x="136" y="102" width="5" height="6" rx="1" />
      </g>

      {/* The rooftop billboard. In 2018 it was a yellow ellipse reading
          STEP JOB; here it is the mark, because type that small is a smudge. */}
      <g>
        <rect x="64" y="38" width="56" height="26" rx="7" fill="#0284c7" />
        <g fill="#ffffff">
          <g opacity="0.5" transform="rotate(-24 78 54)">
            <ellipse cx="78" cy="51" rx="2.6" ry="4" />
            <ellipse cx="78" cy="56" rx="1.9" ry="2" />
          </g>
          <g opacity="0.78" transform="rotate(-24 92 48)">
            <ellipse cx="92" cy="45" rx="2.6" ry="4" />
            <ellipse cx="92" cy="50" rx="1.9" ry="2" />
          </g>
          <g transform="rotate(-24 106 42)">
            <ellipse cx="106" cy="39" rx="2.6" ry="4" />
            <ellipse cx="106" cy="44" rx="1.9" ry="2" />
          </g>
        </g>
        <rect x="86" y="64" width="4" height="10" fill="#0284c7" opacity="0.5" />
      </g>

      {/* The clock, red-rimmed in the original. */}
      <circle cx="268" cy="54" r="20" fill="#ffffff" />
      <circle cx="268" cy="54" r="20" fill="none" stroke="#c6392f" strokeWidth="3" />
      <path
        d="M268 42v12l8 5"
        fill="none"
        stroke="#1c2530"
        strokeWidth="2.6"
        strokeLinecap="round"
      />

      {/* Whoever is working today: the chair, then the figure, then the desk
          in front, so the desk overlaps as it does in a photograph. */}
      <path d="M196 150c0-16 10-24 24-24s24 8 24 24v30h-48z" fill="#c6392f" opacity="0.85" />
      <ellipse cx="220" cy="112" rx="17" ry="19" fill="#f3c9a6" />
      <path
        d="M203 112c0-14 8-22 17-22s17 8 17 22v12c-3-2-5-5-5-10-8 3-20 2-24-6v16c-3 0-5 3-5 8z"
        fill="#3b2a24"
      />
      <path d="M190 182c0-20 13-32 30-32s30 12 30 32z" fill="#1c2530" />
      <path d="M212 152l8 10 8-10z" fill="#ffffff" />

      {/* The desk. */}
      <rect x="44" y="180" width="236" height="12" rx="6" fill="#ffffff" />
      <rect x="60" y="192" width="16" height="48" rx="5" fill="#bae6fd" />
      <rect x="248" y="192" width="16" height="48" rx="5" fill="#bae6fd" />
      <rect x="86" y="192" width="78" height="48" rx="7" fill="#e0f2fe" />
      <g fill="#bae6fd">
        <rect x="96" y="204" width="58" height="4" rx="2" />
        <rect x="96" y="218" width="58" height="4" rx="2" />
      </g>

      {/* The laptop, open towards the figure. */}
      <path d="M118 180l10-44h54l10 44z" fill="#ffffff" opacity="0.9" />
      <path d="M131 142h48l7 32h-62z" fill="url(#scene-screen)" />
      <g fill="#7dd3fc">
        <rect x="138" y="150" width="34" height="3.4" rx="1.7" />
        <rect x="138" y="158" width="26" height="3.4" rx="1.7" />
        <rect x="138" y="166" width="30" height="3.4" rx="1.7" />
      </g>

      {/* The cat, on the desk, where it has been since 2018. */}
      <g transform="translate(196 134) scale(0.72)">
        <CatShapes />
      </g>
    </svg>
  );
}
