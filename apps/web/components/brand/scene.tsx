import { CatShapes } from "@/components/brand/people";

/**
 * The 2018 Android banner, in layers.
 *
 * Nothing is cut out of the base. A part is a *copy* of a limb laid over the
 * top: at rest it sits exactly on the original, and when it turns, the few
 * pixels that peek out from under it are the same black as the limb. Cutting
 * the limb out instead leaves a hole — the artwork drew nothing behind her —
 * and on a dark page a hole is a black gash.
 *
 * Traced from the artwork file (`tools/trace-artwork/`). A flat picture
 * cannot move, so the parts that should — her head, her forearm, each shin —
 * are cut out of the base and written as their own files on the same
 * 800 × 478 grid. Stacking them at the same size puts every part back
 * exactly where it was, and each can then turn about its own joint.
 *
 * The cat is cut from the base by her own colours rather than by a box; a box
 * took a bite out of Mich's shoulder, because the tabby's head overlapped it.
 * The Persian is drawn over the gap in the overlay, which shares the
 * artwork's coordinates so the two cannot drift apart.
 */

const SKIN = "#f7c39f";
const CAT = "translate(566 127.4) scale(2.45)";

/** Each part, and the joint it turns about, as a share of the artwork. */
const HEAD = { animation: "head-tilts", origin: "66% 44.8%" } as const;

/** In painting order. The mug is a layer so that it covers the arm's cut. */
const PARTS = [
  { name: "arm", animation: "arm-types", origin: "63.5% 48.9%" },
  { name: "mug", animation: "", origin: "" },
  { name: "head", animation: HEAD.animation, origin: HEAD.origin },
] as const;

export function DeskScene({ className }: { className?: string }) {
  return (
    <div className={className}>
      <div className="banner-floats relative">
        {/* eslint-disable-next-line @next/next/no-img-element -- an SVG needs
            no optimisation, and next/image would only add a request. */}
        <img src="/artwork/desk-2018.svg" alt="" width={800} height={478} className="w-full" />
        {PARTS.map(({ name, animation, origin }) => (
          // eslint-disable-next-line @next/next/no-img-element -- as above
          <img
            key={name}
            src={`/artwork/desk-2018-${name}.svg`}
            alt=""
            width={800}
            height={478}
            className={`absolute inset-0 h-full w-full ${animation}`}
            style={{ transformOrigin: origin }}
          />
        ))}
        <svg viewBox="0 0 800 478" aria-hidden className="absolute inset-0 h-full w-full">
          {/* Her eyelids: she lives inside a flat image, so a blink is a
              skin-coloured ellipse over each eye, dropping together. */}
          {/* Her eyelids ride with her head, or they blink where her eyes
              used to be. Same animation, same joint. */}
          <g className={HEAD.animation} style={{ transformOrigin: HEAD.origin }}>
            <ellipse className="blink" cx="500.5" cy="103" rx="6.5" ry="5.2" fill={SKIN} />
            <ellipse className="blink" cx="529.5" cy="102.5" rx="6.2" ry="5.2" fill={SKIN} />
          </g>
          {/* Placement on the outer group, animation on the inner one: a CSS
              transform replaces the element's own transform attribute, and
              putting both on one group dropped her to the origin at 1:1. */}
          <g transform={CAT}>
            <g className="cat-breathes">
              <CatShapes />
            </g>
          </g>
        </svg>
      </div>
    </div>
  );
}
