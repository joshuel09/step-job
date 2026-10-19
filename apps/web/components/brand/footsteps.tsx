/**
 * The mark from the 2018 Android app: footprints walking across the tile.
 *
 * Drawn rather than drawn-over. The original was a flat charcoal print on a
 * light blue square; this keeps the walk and the diagonal, fills the tile with
 * a gradient, and fades the trailing steps so the mark reads as movement.
 *
 * Two forms, because one does not work at both ends. `BrandMark` is the tile,
 * white prints on blue, and it is what survives at 20px in a browser tab or
 * beside a wordmark — charcoal-on-blue closes up and prints without a tile
 * dissolve into the page. `Footsteps` is the prints alone, for when they sit
 * large or on colour of their own.
 *
 * Each print is a sole and a heel, which is the shape the original used and
 * the least that still reads as a footprint when it is small.
 */

const PRINTS = [
  { x: 18, y: 43, opacity: 0.45 },
  { x: 32, y: 32, opacity: 0.75 },
  { x: 46, y: 21, opacity: 1 },
];

function Prints({ fill }: { fill: string }) {
  return (
    <g fill={fill}>
      {PRINTS.map(({ x, y, opacity }) => (
        <g key={x} opacity={opacity} transform={`rotate(-24 ${x} ${y + 3})`}>
          <ellipse cx={x} cy={y} rx="5.4" ry="8.2" />
          <ellipse cx={x} cy={y + 10.5} rx="4" ry="4.2" />
        </g>
      ))}
    </g>
  );
}

/** The app icon: white footprints on the brand tile. */
export function BrandMark({
  className,
  gradientId = "sj-tile",
}: {
  className?: string;
  gradientId?: string;
}) {
  return (
    <svg viewBox="0 0 64 64" role="presentation" aria-hidden className={className}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#5cc8f5" />
          <stop offset="100%" stopColor="#0284c7" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="15" fill={`url(#${gradientId})`} />
      <Prints fill="#ffffff" />
    </svg>
  );
}

/** The prints alone, filled with the brand gradient. */
export function Footsteps({
  className,
  gradientId = "sj-footsteps",
}: {
  className?: string;
  gradientId?: string;
}) {
  return (
    <svg viewBox="0 0 64 64" role="presentation" aria-hidden className={className}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#036ba1" />
        </linearGradient>
      </defs>
      <Prints fill={`url(#${gradientId})`} />
    </svg>
  );
}
