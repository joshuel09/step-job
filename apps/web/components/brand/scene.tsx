import { CatShapes } from "@/components/brand/people";

/**
 * The 2018 home header, traced.
 *
 * Not a scene in the brand palette that borrows the subjects — the artwork
 * itself: the window and the glare across it, the skyline, the billboard with
 * its bulbs, the leaning laptop, the desk and its drawers, Mich with the cup,
 * the red chair, the clock. Colours are sampled from the original and taken
 * off the warm cast of the photograph it was shot from, which is why the
 * background is the artwork's blue rather than the brand's.
 *
 * The one departure is the cat, who is the Persian she actually is (#130).
 */

const SKY = "#3fb0dc";
const FRAME = "#eeefe9";
const GLASS = "#b6b9bb";
const GLARE = "#c9cccd";
const BUILDING = "#6e6a66";
const BUILDING_DARK = "#4f4b48";
const LIT = "#c9c9c6";
const YELLOW = "#e9d24f";
const DESK = "#615c57";
const DESK_EDGE = "#4f4a46";
const DRAWERS = "#5e5751";
const LAPTOP = "#c8c6c2";
const LAPTOP_DARK = "#a9a7a3";
const HAIR = "#2a1a12";
const SKIN = "#f0b98f";
const SUIT = "#1c1c1a";
const WHITE = "#fbfbf8";
const RED = "#c6503a";

/** Lit windows as a grid, rather than a hundred hand-placed rectangles. */
function Windows({
  x,
  y,
  cols,
  rows,
  gap = 15,
  size = 8,
  height,
}: {
  x: number;
  y: number;
  cols: number;
  rows: number;
  gap?: number;
  size?: number;
  height?: number;
}) {
  return (
    <g fill={LIT}>
      {Array.from({ length: rows }).flatMap((_, row) =>
        Array.from({ length: cols }).map((_, col) => (
          <rect
            key={`${row}-${col}`}
            x={x + col * gap}
            y={y + row * gap}
            width={size}
            height={height ?? size + 2}
            rx="1"
          />
        )),
      )}
    </g>
  );
}

export function DeskScene({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 1040 640" role="presentation" aria-hidden className={className}>
      <defs>
        <clipPath id="scene-pane">
          <rect x="86" y="96" width="352" height="378" />
        </clipPath>
      </defs>

      <rect width="1040" height="640" rx="26" fill={SKY} />

      {/* --- the window -------------------------------------------------- */}
      <rect x="68" y="60" width="388" height="432" fill={FRAME} />
      <rect x="86" y="96" width="352" height="378" fill={GLASS} />

      <g clipPath="url(#scene-pane)">
        {/* Clouds behind the billboard. */}
        <g fill={GLARE} opacity="0.55">
          <ellipse cx="150" cy="126" rx="42" ry="26" />
          <ellipse cx="236" cy="112" rx="52" ry="30" />
          <ellipse cx="330" cy="130" rx="46" ry="26" />
        </g>

        {/* The skyline. Roofs at different heights, the darker blocks in
            front, and the left building's windows larger than the right's. */}
        <rect x="96" y="226" width="74" height="26" fill={BUILDING} />
        <g fill={BUILDING}>
          <rect x="90" y="252" width="118" height="222" />
          <rect x="288" y="238" width="86" height="236" />
        </g>
        <g fill={BUILDING_DARK}>
          <rect x="208" y="268" width="80" height="206" />
          <rect x="374" y="262" width="64" height="212" />
        </g>
        <rect x="196" y="286" width="64" height="40" fill={GLASS} />

        {/* Windows: tall ones on the near building, small squares beyond. */}
        <Windows x={104} y={282} cols={3} rows={5} gap={26} size={14} height={20} />
        <Windows x={216} y={300} cols={4} rows={6} gap={17} size={9} />
        <Windows x={298} y={266} cols={3} rows={7} gap={22} size={12} height={14} />
        <Windows x={384} y={292} cols={3} rows={6} gap={17} size={9} />

        {/* The billboard, standing on the near building's roof. */}
        <rect x="252" y="236" width="10" height="36" fill="#59544f" />
        <path d="M196 212h124l-14 28H210z" fill="#59544f" />
        <g fill={YELLOW}>
          <circle cx="224" cy="226" r="8" />
          <circle cx="258" cy="226" r="8" />
          <circle cx="292" cy="226" r="8" />
        </g>
        <ellipse cx="258" cy="162" rx="146" ry="70" fill={YELLOW} />
        <text
          x="258"
          y="166"
          textAnchor="middle"
          fontSize="54"
          fontWeight="800"
          letterSpacing="1"
          fill="#1f1d1a"
        >
          <tspan fill="#2a93c7">STEP</tspan> JOB
        </text>
        <text
          x="258"
          y="196"
          textAnchor="middle"
          fontSize="16"
          fontWeight="700"
          letterSpacing="0.6"
          fill="#1f1d1a"
        >
          BOOST YOUR CONFIDENCE
        </text>

        {/* The glare: one wedge across the glass, as in the original. */}
        <path d="M86 96h150L86 330z" fill={GLARE} opacity="0.4" />
        <path d="M306 96h132v58L166 474h-80z" fill={GLARE} opacity="0.22" />
      </g>

      {/* The valance above the window. */}
      <rect x="62" y="40" width="400" height="34" rx="3" fill={FRAME} />

      {/* --- the clock ---------------------------------------------------- */}
      <circle cx="851" cy="131" r="52" fill={RED} />
      <circle cx="851" cy="131" r="43" fill={WHITE} />
      <path
        d="M851 98v33l24 14"
        fill="none"
        stroke="#2b2a27"
        strokeWidth="4"
        strokeLinecap="round"
      />

      {/* --- Mich --------------------------------------------------------- */}
      {/* The chair: backrest behind her, stem and foot below. Measured from
          the artwork at x 700–824, y 272–470. */}
      <path d="M716 272h66c24 0 42 18 42 42v156h-150V314c0-24 18-42 42-42z" fill={RED} />
      <rect x="742" y="470" width="14" height="118" rx="4" fill={FRAME} />
      <rect x="700" y="586" width="100" height="13" rx="6" fill={FRAME} />

      {/* Legs, crossed. Thigh out to the knee, shin back under it, and the
          heel turned the way a crossed ankle turns. Drawn before the torso so
          the hip sits over the top of them. */}
      {/* Scaled about the hip so the heels land inside the frame, as they
          do in the original. */}
      <g transform="translate(740 420) scale(0.82) translate(-740 -420)">
        <path d="M770 404c0 62-34 94-108 134l-22 12-26-42 26-14c62-34 86-54 86-96z" fill={SUIT} />
        <path d="M784 436c0 66-38 100-112 142l-24 14-26-42 28-16c62-34 86-58 86-100z" fill={SUIT} />
        <path d="M614 508l-28 16 26 42 28-16z" fill={SKIN} />
        <path d="M636 566l-28 16 26 42 28-16z" fill={SKIN} />
        <path d="M586 556l20 34-62 24-10-16 30-20z" fill={SUIT} />
        <path d="M536 598h18l6 16h-18z" fill={SUIT} />
        <path d="M608 614l20 34-62 24-10-16 30-20z" fill={SUIT} />
        <path d="M558 656h18l6 16h-18z" fill={SUIT} />
      </g>

      {/* Torso, the arm reaching to the keyboard, the cuff and the hand. */}
      <path d="M688 236c48 0 80 30 80 80v132h-98l-18-132c0-50 14-80 36-80z" fill={SUIT} />
      <path d="M702 288c-2 0-70 28-112 42l12 36c56-16 112-38 112-38z" fill={SUIT} />
      <rect
        x="578"
        y="318"
        width="28"
        height="34"
        rx="7"
        fill={WHITE}
        transform="rotate(-16 592 335)"
      />
      <ellipse cx="558" cy="338" rx="19" ry="14" fill={SKIN} transform="rotate(-16 558 338)" />

      {/* The cup, with the heart. */}
      <rect x="640" y="300" width="58" height="48" rx="7" fill={WHITE} />
      <path d="M698 312h10a10 10 0 0 1 0 20h-10" fill="none" stroke={WHITE} strokeWidth="7" />
      <path d="M669 336c-15-11-17-19-12-23 4-3 9-1 12 3 3-4 8-6 12-3 5 4 3 12-12 23z" fill={RED} />

      {/* Collar and buttons. */}
      <path d="M674 230l20 26 22-26-20-10z" fill={WHITE} />
      <circle cx="700" cy="270" r="9" fill={WHITE} />
      <circle cx="706" cy="298" r="9" fill={WHITE} />

      {/* Head: face, smile, eye, then the bob over all of it. */}
      <ellipse cx="702" cy="156" rx="48" ry="56" fill={SKIN} />
      <path d="M670 182c14 11 31 11 45 0-2 19-12 29-24 29s-20-10-21-29z" fill={WHITE} />
      <circle cx="666" cy="148" r="6" fill={HAIR} />
      <path
        d="M702 60c50 0 82 34 82 86v100c-18 0-28-12-28-30V166c-24 14-68 16-94-6-4 24-10 38-26 42V146c0-52 16-86 66-86z"
        fill={HAIR}
      />

      {/* --- the laptop ---------------------------------------------------- */}
      <path d="M392 228h170l26 122H358z" fill={LAPTOP} />
      <path d="M474 282l15 9v18l-15 9-15-9v-18z" fill={LAPTOP_DARK} opacity="0.6" />
      <path d="M350 350h248l12 16H338z" fill={LAPTOP_DARK} />

      {/* --- the desk ------------------------------------------------------ */}
      <rect x="285" y="346" width="660" height="24" rx="3" fill={DESK} />
      <rect x="285" y="368" width="660" height="10" rx="3" fill={DESK_EDGE} />
      <rect x="903" y="376" width="22" height="236" rx="4" fill={DESK} />
      <rect x="292" y="376" width="179" height="252" rx="4" fill={DRAWERS} />
      <g fill={DESK_EDGE}>
        <rect x="292" y="458" width="179" height="4" />
        <rect x="292" y="540" width="179" height="4" />
      </g>
      <g fill={FRAME}>
        <rect x="359" y="422" width="46" height="9" rx="4" />
        <rect x="359" y="504" width="46" height="9" rx="4" />
        <rect x="359" y="586" width="46" height="9" rx="4" />
      </g>

      {/* --- the cat, on the desk where she has always been ---------------- */}
      <g transform="translate(766 259) scale(1.9)">
        <CatShapes />
      </g>
    </svg>
  );
}
