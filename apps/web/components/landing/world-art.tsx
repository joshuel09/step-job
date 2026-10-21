import { BUILDING, HX, ROOF_SIGN, SLOPE, type Solid, gx, gy } from "@/lib/site";

/**
 * The drawing on the landing page.
 *
 * It is one isometric plate seen from above and to the side: the city, the
 * Step Job building, and the people using it all stand on the same slab.
 * Everything is flat colour inside a single blue outline — no gradients and
 * no shading — which is what makes a scene this busy still read at a glance.
 *
 * The people are drawn flat even though the props are isometric. That is
 * deliberate: a figure in true isometric has to be posed in three dimensions
 * to look right, and at this size it only reads as a smudge.
 *
 * Nothing here is decorative only. Every object is something the product
 * does, and the six that have a marker over them are listed in lib/site.ts.
 */

const LINE = "#0b82c4";
const WHITE = "#ffffff";
const PALE = "#f1fafe";
const B1 = "#ddf2fd";
const B2 = "#bde7fb";
const B3 = "#89d4f6";
const B4 = "#48bdf0";
const B5 = "#0b82c4";
const SKIN = "#fae1d2";

/** One pen for the whole drawing. Fills are set per shape, never here. */
const pen = {
  stroke: LINE,
  strokeWidth: 3.4,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;
const nib = { ...pen, strokeWidth: 2.4 } as const;

/**
 * A cuboid standing on the plate: the two faces turned towards us and the
 * top. `base` lifts it, so a monitor can stand on a desk.
 */
function Box({
  u,
  v,
  du,
  dv,
  h,
  base = 0,
  top = WHITE,
  left = B1,
  right = B2,
}: {
  u: number;
  v: number;
  du: number;
  dv: number;
  h: number;
  base?: number;
  top?: string;
  left?: string;
  right?: string;
}) {
  const at = (uu: number, vv: number, lift: number) => `${gx(uu, vv)} ${gy(uu, vv) - lift}`;
  const lo = base;
  const hi = base + h;
  const A = (l: number) => at(u - du, v - dv, l);
  const B = (l: number) => at(u + du, v - dv, l);
  const C = (l: number) => at(u + du, v + dv, l);
  const D = (l: number) => at(u - du, v + dv, l);
  return (
    <g>
      <path d={`M${B(lo)}L${C(lo)}L${C(hi)}L${B(hi)}Z`} fill={right} {...pen} />
      <path d={`M${C(lo)}L${D(lo)}L${D(hi)}L${C(hi)}Z`} fill={left} {...pen} />
      <path d={`M${A(hi)}L${B(hi)}L${C(hi)}L${D(hi)}Z`} fill={top} {...pen} />
    </g>
  );
}

/**
 * Transforms that let a face of a box be drawn in flat coordinates: put a
 * rect at (0,0) and it lands on the top-left corner of that face. Local x
 * runs across the face, local y straight down it.
 */
function leftFace({ u, v, du, dv, h, base = 0 }: Solid) {
  return `matrix(1 ${SLOPE} 0 1 ${gx(u - du, v + dv)} ${gy(u - du, v + dv) - base - h})`;
}

function rightFace({ u, v, du, dv, h, base = 0 }: Solid) {
  return `matrix(-1 ${SLOPE} 0 1 ${gx(u + du, v - dv)} ${gy(u + du, v - dv) - base - h})`;
}

/** The lid of a box: local x runs along +u, local y along +v. */
function topFace({ u, v, du, dv, h, base = 0 }: Solid) {
  const x = gx(u - du, v - dv);
  const y = gy(u - du, v - dv) - base - h;
  return `matrix(1 ${SLOPE} -1 ${SLOPE} ${x} ${y})`;
}

/** A limb: one rounded stroke in the outline colour with a thinner one over it. */
function Limb({
  d,
  fill,
  w = 10,
  light = false,
}: {
  d: string;
  fill: string;
  w?: number;
  light?: boolean;
}) {
  return (
    <>
      <path
        d={d}
        fill="none"
        stroke={LINE}
        strokeWidth={w + (light ? 4 : 6)}
        strokeLinecap="round"
      />
      <path d={d} fill="none" stroke={fill} strokeWidth={w} strokeLinecap="round" />
    </>
  );
}

/**
 * How a body is turned. Turning somebody is not a matter of redrawing the
 * head: the shoulders narrow as they come side-on, and the feet have to
 * point where the person is looking. A figure with its back to us and its
 * toes towards us is the thing that makes a scene look wrong.
 *
 * Shoes carry their own angle; side-on both point the same way instead of
 * splaying, and from behind they are heels tucked under the legs.
 */
const BUILD = {
  front: {
    narrow: false,
    shoes: [
      { cx: -13, cy: -5, rx: 11, ry: 6, rot: -24 },
      { cx: 13, cy: -5, rx: 11, ry: 6, rot: 24 },
    ],
  },
  side: {
    narrow: false,
    shoes: [
      { cx: -14, cy: -12, rx: 12, ry: 6.5, rot: -18 },
      { cx: 14, cy: -4, rx: 13, ry: 7, rot: 16 },
    ],
  },
  profile: {
    narrow: true,
    shoes: [
      { cx: 1, cy: -13, rx: 11, ry: 5.5, rot: 10 },
      { cx: 11, cy: -4, rx: 12, ry: 6, rot: 12 },
    ],
  },
  away: {
    narrow: false,
    shoes: [
      { cx: -9, cy: -12, rx: 8, ry: 5, rot: 4 },
      { cx: 9, cy: -8, rx: 8, ry: 5, rot: -4 },
    ],
  },
} as const;

/* The body, with shoulders that slope and a waist. S is the half-width at
   the shoulder and H at the hem, so a figure in a dress can be built on a
   slimmer frame than one in trousers without redrawing the path by hand. */
const torsoPath = (S: number, H: number) =>
  `M${11 - S} -100h${2 * (S - 11)}c6 0 10 5 11 11l${H - S} 33a8 8 0 0 1-8 8h${16 - 2 * H}` +
  `a8 8 0 0 1-8-8l${H - S} -33c0-6 5-11 11-11z`;

/* A dress is not the same shape as a coat: the bodice draws in at the waist
   and the skirt flares out from it, so the silhouette curves instead of
   falling straight from the shoulder. */
const BODICE = {
  wide: "M-8 -100h16c6 0 10 5 11 11c0 9-2 17-6 25h-26c-4-8-6-16-6-25c1-6 5-11 11-11z",
  narrow: "M-5 -100h10c6 0 10 5 11 11c0 9-2 17-5 25h-22c-3-8-5-16-5-25c1-6 5-11 11-11z",
};
const SKIRT = {
  wide: "M-13 -66h26c3 10 6 20 9 28a4 4 0 0 1-4 5h-36a4 4 0 0 1-4-5c3-8 6-18 9-28z",
  narrow: "M-11 -66h22c3 10 5 19 7 28a4 4 0 0 1-4 5h-30a4 4 0 0 1-4-5c2-9 4-18 7-28z",
};

/* Trousers are one shape split by a line, rather than two bars with daylight
   between them; under a skirt the legs are two short bars. */
const TROUSERS = {
  wide: "M-16 -48h32v38h-13v-26h-6v26h-13z",
  narrow: "M-13 -48h26v38h-11v-26h-4v26h-11z",
};
const BARE_LEGS = "M-10 -36h7v28h-7zM3 -36h7v28h-7z";

/* An arm leaves the shoulder, bends at the elbow and ends in a hand. The far
   arm passes behind the body, the near one crosses in front of it. */
const ARMS = {
  hang: (s: number) => ({
    far: { d: `M${-s} -88l-6 20-1 20`, hand: [-s - 6, -48] },
    near: { d: `M${s} -88l6 20 1 20`, hand: [s + 6, -48] },
  }),
  down: (s: number) => ({
    far: { d: `M${-s} -88l-6 20-1 20`, hand: [-s - 6, -48] },
    near: { d: `M${s} -88l-4 22-8 16`, hand: [s - 12, -50] },
  }),
  wave: (s: number) => ({
    far: { d: `M${-s} -88l-6 20-1 20`, hand: [-s - 6, -48] },
    near: { d: `M${s} -88c10 1 15-6 13-18`, hand: [s + 13, -106] },
  }),
  point: (s: number) => ({
    far: { d: `M${-s} -88l-6 20-1 20`, hand: [-s - 6, -48] },
    near: { d: `M${s} -88l15 9 11 0`, hand: [s + 26, -79] },
  }),
  type: (s: number) => ({
    far: { d: `M${-s} -88l-10 18 10 9`, hand: [-s, -61] },
    near: { d: `M${s} -88l10 18-10 9`, hand: [s, -61] },
  }),
  talk: (s: number) => ({
    far: { d: `M${-s} -88l-6 20-1 20`, hand: [-s - 6, -48] },
    near: { d: `M${s} -88l9-5 8-13`, hand: [s + 17, -106] },
  }),
  gesture: (s: number) => ({
    far: { d: `M${-s} -88l-8 16 2 20`, hand: [-s - 6, -52] },
    near: { d: `M${s} -88c12 0 18-8 16-19`, hand: [s + 16, -107] },
  }),
  think: (s: number) => ({
    far: { d: `M${-s} -88l-3 20 16 3`, hand: [-s + 13, -65] },
    near: { d: `M${s} -88l3 20-4-25`, hand: [s - 1, -93] },
  }),
  phone: (s: number) => ({
    far: { d: `M${-s} -88l-6 20-1 20`, hand: [-s - 6, -48] },
    near: { d: `M${s} -88l9 10-10-28`, hand: [s - 1, -106] },
  }),
  hold: (s: number) => ({
    far: { d: `M${-s} -88l-6 14 14 6`, hand: [-s + 8, -68] },
    near: { d: `M${s} -88l6 14-14 6`, hand: [s - 8, -68] },
  }),
} as const;

/**
 * Somebody, drawn at the same three-quarter angle as the boxes they stand
 * among. `face` turns the whole body, not only the head.
 * About 137 units tall, which puts the Step Job building at two of them.
 */
function Person({
  u,
  v,
  lift = 0,
  s = 0.74,
  flip = false,
  top = B2,
  legs = WHITE,
  arms = "down",
  face = "side",
  dress = false,
  className,
}: {
  u: number;
  v: number;
  lift?: number;
  s?: number;
  flip?: boolean;
  top?: string;
  legs?: string;
  arms?: keyof typeof ARMS;
  face?: keyof typeof BUILD;
  /** Long hair and a dress. The two go together: a figure is either one or
   *  the other, never short hair in a skirt. */
  dress?: boolean;
  className?: string;
}) {
  const build = BUILD[face];
  const cut = build.narrow ? "narrow" : "wide";
  // A dress sits on a slimmer frame: the same width as a coat made the
  // figures look heavy.
  const shoulder = build.narrow ? (dress ? 15 : 18) : dress ? 19 : 22;
  const hem = build.narrow ? (dress ? 16 : 19) : dress ? 20 : 24;
  const { far, near } = ARMS[arms](shoulder - 3);
  const hand = (at: readonly number[]) => (
    <circle cx={at[0]} cy={at[1]} r="5.4" fill={SKIN} {...nib} />
  );
  const shoe = (i: 0 | 1) => {
    const { cx, cy, rx, ry, rot } = build.shoes[i];
    return (
      <ellipse
        cx={cx}
        cy={cy}
        rx={rx}
        ry={ry}
        fill={B5}
        transform={`rotate(${rot} ${cx} ${cy})`}
        {...nib}
      />
    );
  };

  return (
    // Placement on the outer group, animation on the inner one: a CSS
    // transform replaces an SVG transform attribute instead of adding to it,
    // so animating this group directly drops the figure onto the origin.
    <g transform={`translate(${gx(u, v)} ${gy(u, v) - lift}) scale(${flip ? -s : s} ${s})`}>
      <g className={className}>
        {dress ? (
          <g>
            <path d={BARE_LEGS} fill={legs} {...pen} />
            {shoe(0)}
            {shoe(1)}
            <path d={SKIRT[cut]} fill={top} {...pen} />
          </g>
        ) : (
          <g>
            <path d={TROUSERS[cut]} fill={legs} {...pen} />
            {shoe(0)}
            {shoe(1)}
          </g>
        )}

        {face === "profile" ? null : (
          <g>
            <Limb d={far.d} fill={top} w={8} />
            {hand(far.hand)}
          </g>
        )}

        <path d={dress ? BODICE[cut] : torsoPath(shoulder, hem)} fill={top} {...pen} />
        {face === "away" ? <path d="M-11 -98q11 8 22 0" fill="none" {...nib} /> : null}

        <Limb d={near.d} fill={top} w={8} light={arms === "down"} />
        {hand(near.hand)}
        {arms === "phone" ? (
          <rect
            x={(near.hand[0] ?? 0) - 3}
            y={(near.hand[1] ?? 0) - 8}
            width="7"
            height="15"
            rx="2"
            fill={B5}
            transform={`rotate(10 ${near.hand[0] ?? 0} ${near.hand[1] ?? 0})`}
          />
        ) : null}
        {arms === "hold" ? (
          <g transform="rotate(-8 0 -72)">
            <rect x="-13" y="-82" width="26" height="19" rx="2" fill={WHITE} {...nib} />
            <rect x="-9" y="-77" width="18" height="3" rx="1.5" fill={B2} />
            <rect x="-9" y="-71" width="12" height="3" rx="1.5" fill={B2} />
          </g>
        ) : null}

        {/* The head is one silhouette: the hair sits above and behind the
            face rather than beside it, which is what made the face look as
            though it was sliding off the skull. */}
        {face === "away" ? (
          <ellipse cx="0" cy="-114" rx="18" ry="18" fill={B5} {...pen} />
        ) : face === "front" ? (
          <g>
            <ellipse cx="0" cy="-120" rx="19" ry="17" fill={B5} {...pen} />
            <ellipse cx="0" cy="-110" rx="15" ry="16" fill={SKIN} {...pen} />
            <circle cx="-6" cy="-112" r="2.3" fill={LINE} />
            <circle cx="6" cy="-112" r="2.3" fill={LINE} />
          </g>
        ) : face === "profile" ? (
          <g>
            <ellipse cx="-3" cy="-119" rx="19" ry="17" fill={B5} {...pen} />
            <ellipse cx="4" cy="-110" rx="14" ry="16" fill={SKIN} {...pen} />
            {dress ? (
              <path d="M-17 -116c-3 7-3 15 0 21l7-2c-3-6-3-13-1-18z" fill={B5} {...nib} />
            ) : null}
            <circle cx="9" cy="-112" r="2.3" fill={LINE} />
          </g>
        ) : (
          <g>
            <ellipse cx="-1" cy="-120" rx="19" ry="17" fill={B5} {...pen} />
            <ellipse cx="2" cy="-110" rx="15" ry="16" fill={SKIN} {...pen} />
            {dress ? (
              <path d="M-16 -116c-3 7-3 15 0 21l7-2c-3-6-3-13-1-18z" fill={B5} {...nib} />
            ) : null}
            <circle cx="-2" cy="-112" r="2.3" fill={LINE} />
            <circle cx="8" cy="-112" r="2.3" fill={LINE} />
          </g>
        )}
      </g>
    </g>
  );
}

/**
 * makaka, whole and small. The first version was a loaf — a big head on a
 * hunched blob — which at this size read as a hunched person rather than a
 * cat. A cat needs four legs, a tail and a body longer than it is tall.
 */
function Makaka({ u, v, lift = 0, s = 1 }: { u: number; v: number; lift?: number; s?: number }) {
  return (
    <g transform={`translate(${gx(u, v)} ${gy(u, v) - lift}) scale(${s})`}>
      <g className="breathe-slow">
        {/* the tail curls up behind her */}
        <Limb d="M-23 -17c-13 1-19-7-15-16" fill={WHITE} w={5} light />

        {/* four legs, the near pair a little forward */}
        <Limb d="M-15 -13V-3" fill={WHITE} w={5} light />
        <Limb d="M6 -13V-3" fill={WHITE} w={5} light />
        <Limb d="M-8 -11V-1" fill={WHITE} w={5} light />
        <Limb d="M13 -11V-1" fill={WHITE} w={5} light />

        <ellipse cx="-3" cy="-20" rx="21" ry="13" fill={WHITE} {...nib} />
        <circle cx="18" cy="-31" r="11" fill={WHITE} {...nib} />
        <path d="M10 -38l-3-10 10 5zM26 -38l3-10-10 5z" fill={WHITE} {...nib} />
        <circle cx="14" cy="-32" r="1.8" fill={LINE} />
        <circle cx="23" cy="-32" r="1.8" fill={LINE} />
        <path d="M18.5 -28l-2.5-2.5h5z" fill={LINE} />
        <path
          d="M13 -29l-7-1M13 -27h-7M13 -25l-7 2M24 -29l7-1M24 -27h7M24 -25l7 2"
          fill="none"
          stroke={LINE}
          strokeWidth="1.4"
          strokeLinecap="round"
        />
      </g>
    </g>
  );
}

/** A table or a bench: four legs and a slab. */
function Table({ u, v, du, dv, h }: { u: number; v: number; du: number; dv: number; h: number }) {
  return (
    <g>
      {(
        [
          [-1, -1],
          [1, -1],
          [1, 1],
          [-1, 1],
        ] as const
      ).map(([su, sv]) => {
        const lx = gx(u + su * du, v + sv * dv);
        const ly = gy(u + su * du, v + sv * dv);
        return (
          <path
            key={`${su}${sv}`}
            d={`M${lx} ${ly}V${ly - h + 9}`}
            fill="none"
            stroke={LINE}
            strokeWidth="6"
            strokeLinecap="round"
          />
        );
      })}
      <Box u={u} v={v} du={du} dv={dv} h={9} base={h - 9} top={WHITE} left={B1} right={B2} />
    </g>
  );
}

/**
 * A desktop computer: a screen on a stand, a keyboard in front of it and the
 * tower beside it. Two bare screens sitting on a desk read as display units
 * in a shop rather than as somebody's machine.
 */
function DesktopPC({ u, v, lift }: { u: number; v: number; lift: number }) {
  const foot: Solid = { u, v: v - 0.03, du: 0.035, dv: 0.014, h: 3, base: lift };
  const screen: Solid = { u, v: v - 0.03, du: 0.075, dv: 0.014, h: 34, base: lift + 14 };
  const keys: Solid = { u: u + 0.045, v: v + 0.075, du: 0.058, dv: 0.025, h: 4, base: lift };
  const tower: Solid = { u: u + 0.115, v: v + 0.01, du: 0.024, dv: 0.021, h: 34, base: lift };
  const neck = `M${gx(u, v - 0.03)} ${gy(u, v - 0.03) - lift - 3}v-12`;
  const keyRow = 2 * keys.du * HX;

  return (
    <g>
      <Box {...foot} top={B2} left={B1} right={B2} />
      <path d={neck} fill="none" stroke={LINE} strokeWidth="7" strokeLinecap="round" />
      <path d={neck} fill="none" stroke={B1} strokeWidth="3" strokeLinecap="round" />

      <Box {...screen} top={B1} left={WHITE} right={B2} />
      <g transform={leftFace(screen)}>
        <rect
          x="5"
          y="5"
          width={2 * screen.du * HX - 10}
          height={screen.h - 13}
          rx="3"
          fill={B2}
          {...nib}
        />
      </g>

      <Box {...keys} top={WHITE} left={B1} right={B2} />
      <g transform={topFace(keys)}>
        {[0, 1, 2].map((row) => (
          <rect
            key={row}
            x="5"
            y={4 + row * 4.5}
            width={keyRow - 10}
            height="2.6"
            rx="1.3"
            fill={B2}
          />
        ))}
      </g>

      <Box {...tower} top={B1} left={WHITE} right={B2} />
      <g transform={leftFace(tower)}>
        <rect x="4" y="6" width={2 * tower.du * HX - 8} height="4" rx="2" fill={B2} />
        <rect x="4" y="13" width={2 * tower.du * HX - 8} height="3" rx="1.5" fill={B2} />
        <circle cx="8" cy="24" r="2.6" fill={B4} />
      </g>
    </g>
  );
}

/**
 * A tower in the skyline. Windows on both faces it shows us, because an
 * untouched white box reads as a crate rather than a building.
 */
function Tower({ u, v, du, dv, h }: { u: number; v: number; du: number; dv: number; h: number }) {
  const box: Solid = { u, v, du, dv, h };
  const windows = (w: number) => {
    const cols = Math.max(1, Math.floor((w - 16) / 46));
    const rows = Math.max(1, Math.floor((h - 26) / 48));
    const left = (w - cols * 46 + 12) / 2;
    return Array.from({ length: rows }, (_, r) =>
      Array.from({ length: cols }, (_, c) => (
        <rect
          key={`${r}-${c}`}
          x={left + c * 46}
          y={26 + r * 48}
          width="34"
          height="28"
          rx="4"
          fill={B2}
        />
      )),
    );
  };
  return (
    <g>
      <Box {...box} top={WHITE} left={PALE} right={B1} />
      <g transform={leftFace(box)}>{windows(2 * du * HX)}</g>
      <g transform={rightFace(box)}>{windows(2 * dv * HX)}</g>
    </g>
  );
}

/** A sheet of paper standing on edge, which is how documents appear here. */
function Sheet({
  u,
  v,
  w,
  h,
  lean = 0,
  lines = 4,
}: {
  u: number;
  v: number;
  w: number;
  h: number;
  lean?: number;
  lines?: number;
}) {
  const x = gx(u, v);
  const y = gy(u, v);
  return (
    <g>
      <path
        d={`M${x} ${y}l${w} ${w * SLOPE}l${lean} ${-h}l${-w} ${-w * SLOPE}z`}
        fill={WHITE}
        {...pen}
      />
      <g transform={`matrix(1 ${SLOPE} 0 1 ${x + lean} ${y + lean * SLOPE - h})`}>
        {Array.from({ length: lines }, (_, i) => (
          <rect
            key={i}
            x="9"
            y={14 + i * ((h - 24) / lines)}
            width={i === lines - 1 ? (w - 18) * 0.55 : w - 18}
            height="5"
            rx="2.5"
            fill={B2}
          />
        ))}
      </g>
    </g>
  );
}

/** A tree. One mass, so no outline crosses another. */
function Tree({ u, v, s = 1 }: { u: number; v: number; s?: number }) {
  return (
    <g transform={`translate(${gx(u, v)} ${gy(u, v)}) scale(${s})`}>
      <Limb d="M0 0V-44" fill={B2} w={9} />
      <ellipse cx="0" cy="-74" rx="33" ry="36" fill={B2} {...pen} />
    </g>
  );
}

/** The broadcast tower, because a Tokyo skyline without one is somewhere else. */
function BroadcastTower({ u, v, h = 250 }: { u: number; v: number; h?: number }) {
  const x = gx(u, v);
  const y = gy(u, v);
  return (
    <g transform={`translate(${x} ${y})`}>
      <path d={`M-36 0L-11 ${-h}h22L36 0z`} fill={B1} {...pen} />
      <path d={`M-27 ${-h * 0.36}h54M-20 ${-h * 0.62}h40`} fill="none" {...nib} />
      <path d={`M0 ${-h}v-22`} fill="none" {...nib} />
      <circle cx="0" cy={-h - 26} r="5" fill={B4} {...nib} />
    </g>
  );
}

/**
 * The plane, towing the slogan behind its tail the way a real banner plane
 * does. Placement sits on the outer group and the flight on the inner one.
 */
function BannerPlane({ y }: { y: number }) {
  return (
    <g transform={`translate(0 ${y})`}>
      <g className="fly">
        {/* the banner, trailing from the tail */}
        <path d="M-150 -2h44" fill="none" {...nib} />
        <path d="M-150 -34H-520l24 28-24 28h370z" fill={B5} stroke={B5} strokeWidth="3.4" />
        <text
          x="-330"
          y="-8"
          textAnchor="middle"
          fontSize="27"
          fontWeight="800"
          letterSpacing="1.5"
          fill={WHITE}
          fontFamily="inherit"
        >
          STEP JOB
        </text>
        <text
          x="-330"
          y="13"
          textAnchor="middle"
          fontSize="13"
          fontWeight="700"
          letterSpacing="2"
          fill={WHITE}
          fontFamily="inherit"
        >
          BOOST YOUR CONFIDENCE
        </text>

        {/* The plane itself is drawn full size and then taken down to three
            quarters about its tail root, so the banner still meets the tail. */}
        <g transform="translate(-23.3 0) scale(0.78)">
          {/* tail first, so the fuselage sits over its root */}
          <path d="M-106 -2l14-50h20l8 50z" fill={B3} {...pen} />
          <path d="M-120 8h34v16h-34z" fill={B3} {...pen} />

          <rect x="-106" y="-2" width="192" height="42" rx="20" fill={WHITE} {...pen} />
          <rect x="-96" y="3" width="176" height="12" rx="6" fill={B4} />
          <rect x="-34" y="27" width="106" height="16" rx="8" fill={B3} {...pen} />

          <path d="M4 -2q2-30 24-30h22q16 0 20 30z" fill={WHITE} {...pen} />
          <path d="M20 -7q2-19 14-19h13q10 0 12 19z" fill={B2} {...nib} />
          <path d="M31 -32v-15" fill="none" {...nib} />

          <rect x="76" y="-2" width="16" height="42" rx="7" fill={B3} {...pen} />
          <rect x="96" y="-28" width="8" height="26" rx="4" fill={B5} />
          <rect x="96" y="28" width="8" height="26" rx="4" fill={B5} />
          <circle cx="100" cy="19" r="7" fill={B5} />

          <path d="M-16 43v9M46 43v9" fill="none" {...nib} />
          <circle cx="-16" cy="59" r="10" fill={WHITE} {...pen} />
          <circle cx="46" cy="59" r="10" fill={WHITE} {...pen} />
        </g>
      </g>
    </g>
  );
}

function Cloud({
  x,
  y,
  s = 1,
  className,
}: {
  x: number;
  y: number;
  s?: number;
  className?: string;
}) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <g className={className}>
        <path
          d="M0 0a24 24 0 0 1 46-10 20 20 0 0 1 30 10 17 17 0 0 1-2 34H15A17 17 0 0 1 0 0z"
          fill={WHITE}
          {...pen}
        />
      </g>
    </g>
  );
}

/** One floor of the Step Job building, drawn flat on the building's face. */
function Floor({
  y,
  w,
  h,
  kind,
}: {
  y: number;
  w: number;
  h: number;
  kind: "rirekisho" | "import" | "profile";
}) {
  const line = (x: number, ly: number, lw: number) => (
    <rect key={`${x}-${ly}`} x={x} y={ly} width={lw} height="5" rx="2.5" fill={B2} />
  );
  return (
    <g>
      <rect x="16" y={y} width={w} height={h} rx="8" fill={WHITE} {...nib} />
      {kind === "rirekisho" ? (
        <g>
          <rect x="28" y={y + 12} width="34" height="42" rx="4" fill={B1} {...nib} />
          <circle cx="45" cy={y + 28} r="8" fill={B2} />
          <path d={`M33 ${y + 50}a12 12 0 0 1 24 0z`} fill={B2} />
          {[0, 1, 2, 3].map((i) => line(72, y + 13 + i * 11, w - 70 - (i === 3 ? 40 : 0)))}
        </g>
      ) : kind === "import" ? (
        <g>
          <rect x="28" y={y + 12} width="48" height="42" rx="4" fill={B1} {...nib} />
          {[0, 1, 2].map((i) => line(34, y + 19 + i * 11, 36))}
          <path d={`M86 ${y + 33}h24`} fill="none" stroke={B5} strokeWidth="3" />
          <path d={`M104 ${y + 27}l7 6-7 6`} fill="none" stroke={B5} strokeWidth="3" />
          <rect x="118" y={y + 12} width="48" height="42" rx="4" fill={B1} {...nib} />
          <path d={`M128 ${y + 34}l8 9 16-18`} fill="none" stroke={B4} strokeWidth="4" />
        </g>
      ) : (
        <g>
          <circle cx="46" cy={y + 32} r="17" fill={B1} {...nib} />
          <circle cx="46" cy={y + 26} r="6" fill={B2} />
          <path d={`M34 ${y + 44}a12 12 0 0 1 24 0z`} fill={B2} />
          {[0, 1, 2].map((i) => line(74, y + 16 + i * 13, w - 72 - (i === 2 ? 46 : 0)))}
        </g>
      )}
    </g>
  );
}

export function WorldArt() {
  const plate = {
    left: `${gx(-1, 1)} ${gy(-1, 1)}`,
    back: `${gx(-1, -1)} ${gy(-1, -1)}`,
    right: `${gx(1, -1)} ${gy(1, -1)}`,
    front: `${gx(1, 1)} ${gy(1, 1)}`,
  };
  const t = 36;

  return (
    <>
      <defs>
        <pattern id="sky-dots" width="20" height="20" patternUnits="userSpaceOnUse">
          <circle cx="3" cy="3" r="1.7" fill={WHITE} opacity="0.85" />
        </pattern>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#d9effb" />
          <stop offset="100%" stopColor={PALE} />
        </linearGradient>
      </defs>

      <rect width="1600" height="800" fill="url(#sky)" />
      <rect width="1600" height="800" fill="url(#sky-dots)" />

      <Cloud x={620} y={196} s={0.8} className="drift-slower" />
      <Cloud x={1318} y={174} s={1} className="drift-slow" />
      <Cloud x={1462} y={250} s={0.64} className="drift" />

      <BannerPlane y={74} />

      {/* --- the plate ---------------------------------------------------- */}
      <path
        d={`M${plate.left}L${plate.left.split(" ")[0]} ${Number(plate.left.split(" ")[1]) + t}L${
          plate.front.split(" ")[0]
        } ${Number(plate.front.split(" ")[1]) + t}L${plate.front}Z`}
        fill={B2}
        {...pen}
      />
      <path
        d={`M${plate.right}L${plate.right.split(" ")[0]} ${Number(plate.right.split(" ")[1]) + t}L${
          plate.front.split(" ")[0]
        } ${Number(plate.front.split(" ")[1]) + t}L${plate.front}Z`}
        fill={B3}
        {...pen}
      />
      <path
        d={`M${plate.left}L${plate.back}L${plate.right}L${plate.front}Z`}
        fill={PALE}
        {...pen}
      />

      {/* footprints crossing the plate towards the door */}
      {(
        [
          [-0.55, 0.95],
          [-0.4, 0.83],
          [-0.25, 0.71],
          [-0.1, 0.59],
          [0.05, 0.47],
          [0.2, 0.35],
          [0.35, 0.23],
        ] as const
      ).map(([fu, fv], i) => (
        <ellipse
          key={fu}
          cx={gx(fu, fv) + (i % 2 ? 9 : -9)}
          cy={gy(fu, fv)}
          rx="9"
          ry="5"
          fill={B2}
          opacity={0.35 + i * 0.09}
        />
      ))}

      {/* --- the city, back to front -------------------------------------- */}
      <BroadcastTower u={-0.85} v={-0.85} h={190} />
      <Tower u={-0.45} v={-0.95} du={0.1} dv={0.09} h={200} />
      <Tower u={-0.6} v={-0.95} du={0.07} dv={0.07} h={150} />
      <Tower u={-0.6} v={-0.9} du={0.08} dv={0.08} h={175} />
      <Tower u={-0.25} v={-0.9} du={0.08} dv={0.08} h={245} />
      <Tower u={0.12} v={-0.92} du={0.1} dv={0.09} h={175} />
      <Tower u={0.34} v={-0.98} du={0.09} dv={0.08} h={160} />

      {/* --- the Step Job building ---------------------------------------- */}
      <g>
        <Box {...BUILDING} top={B1} left={WHITE} right={B2} />
        <g transform={leftFace(BUILDING)}>
          <Floor y={24} w={174} h={70} kind="rirekisho" />
          <Floor y={104} w={174} h={70} kind="import" />
          <Floor y={184} w={174} h={70} kind="profile" />
        </g>
        <g transform={rightFace(BUILDING)}>
          {Array.from({ length: 5 }, (_, row) =>
            Array.from({ length: 3 }, (_, col) => (
              <rect
                key={`${row}-${col}`}
                x={22 + col * 50}
                y={26 + row * 48}
                width="34"
                height="30"
                rx="4"
                fill={WHITE}
                opacity="0.9"
              />
            )),
          )}
        </g>

        {/* the sign on the roof */}
        <Box {...ROOF_SIGN} top={B4} left={B5} right={B4} />
        <g transform={leftFace(ROOF_SIGN)}>
          {(
            [
              [26, 20, 0.5],
              [52, 26, 0.75],
              [78, 32, 1],
            ] as const
          ).map(([fx, fy, o]) => (
            <g key={fx} opacity={o} transform={`rotate(-16 ${fx} ${fy})`}>
              <ellipse cx={fx} cy={fy} rx="4.6" ry="7" fill={WHITE} />
              <ellipse cx={fx} cy={fy + 10} rx="3.2" ry="3.6" fill={WHITE} />
            </g>
          ))}
        </g>

        {/* the door, on the ground floor's near corner */}
        <g transform={rightFace(BUILDING)}>
          <path d="M132 190h38v80h-38z" fill={B1} {...nib} />
          <circle cx="140" cy="232" r="3.4" fill={LINE} />
        </g>
      </g>

      <Tower u={0.88} v={-0.8} du={0.1} dv={0.09} h={215} />

      {/* the desk by the window, and somebody at it with their back to us */}
      <g>
        <Table u={0.25} v={0.02} du={0.16} dv={0.085} h={46} />
        <DesktopPC u={0.22} v={-0.01} lift={46} />
        <Person u={0.4} v={0.28} s={0.72} top={B3} arms="type" face="away" className="breathe" />
      </g>

      {/* two in the plaza behind, each doing their own thing rather than
          mirroring each other: one on a call, one reading what she is
          holding */}
      <Person u={-0.5} v={-0.3} s={0.72} top={B4} legs={B1} arms="phone" className="breathe" />
      <Person
        u={-0.4}
        v={-0.45}
        s={0.68}
        top={WHITE}
        legs={B2}
        arms="hold"
        face="front"
        className="breathe-slow"
      />

      {/* on the pavement: one crossing the forecourt, one at the door */}
      <Person u={0.44} v={-0.04} s={0.78} top={B2} legs={B1} dress className="breathe-slow" />
      <Person
        u={0.8}
        v={-0.6}
        s={0.7}
        top={WHITE}
        legs={B3}
        arms="hang"
        dress
        className="breathe"
      />
      <Person
        u={0.15}
        v={0.35}
        s={0.72}
        top={B3}
        face="profile"
        arms="point"
        className="breathe-slow"
      />

      {/* the two of us, mid-conversation, and the cat ignoring both */}
      <g>
        <Person u={0.46} v={0.86} s={0.76} top={B4} arms="talk" face="front" className="breathe" />
        <Person
          u={0.58}
          v={0.78}
          s={0.76}
          top={B3}
          arms="gesture"
          face="away"
          flip
          className="breathe-slow"
        />
        <Makaka u={0.7} v={0.7} s={0.78} />
      </g>

      {/* two of them over a document */}
      <g>
        <Person
          u={0.8}
          v={0.46}
          s={0.7}
          top={B4}
          arms="think"
          face="profile"
          dress
          className="breathe-slow"
        />
        <Table u={0.82} v={0.54} du={0.1} dv={0.09} h={40} />
        <Sheet u={0.78} v={0.52} w={46} h={34} lean={6} lines={3} />
      </g>

      {/* the stories: the long accounts, and somebody reading them */}
      <g>
        <Person
          u={0.88}
          v={0.16}
          s={0.72}
          top={B3}
          arms="point"
          face="profile"
          dress
          className="breathe"
        />
        <Sheet u={0.86} v={0.06} w={78} h={104} lean={10} lines={5} />
        <Sheet u={0.86} v={-0.1} w={70} h={88} lean={8} lines={4} />
      </g>
    </>
  );
}
