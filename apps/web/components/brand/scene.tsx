import { CatShapes } from "@/components/brand/people";

/**
 * The 2018 home header.
 *
 * Not drawn again — traced from the artwork itself and served from
 * `public/artwork/desk-2018.svg`. Two attempts at drawing it by hand got the
 * window and the desk close and the figure wrong, which is the part a person
 * looks at. `tools/trace-artwork/` has the pipeline that produced the file.
 *
 * The cat was taken out of the trace, and the Persian is placed over the gap.
 * These percentages are where the original cat sat: x 756–904, y 248–331 of
 * the artwork's 1040 × 640, with her feet on the desk line.
 */
const CAT = { left: "72.7%", top: "34.4%", width: "14.2%" };

export function DeskScene({ className }: { className?: string }) {
  return (
    <div className={className}>
      <div className="relative">
        {/* eslint-disable-next-line @next/next/no-img-element -- an SVG needs
            no optimisation, and next/image would only add a request. */}
        <img src="/artwork/desk-2018.svg" alt="" width={1040} height={640} className="w-full" />
        <svg viewBox="0 0 64 48" aria-hidden className="absolute" style={CAT}>
          <CatShapes />
        </svg>
      </div>
    </div>
  );
}
