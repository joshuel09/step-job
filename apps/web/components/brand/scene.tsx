import { CatShapes } from "@/components/brand/people";

/**
 * The 2018 Android banner.
 *
 * Traced from the artwork file rather than drawn again, and rather than
 * traced from a photograph of a phone, which is what the first few attempts
 * had to work from. `tools/trace-artwork/` has the pipeline.
 *
 * The cat is cut out of the trace and the Persian drawn over the gap. These
 * percentages are the corner the original cat occupied — x 566–723 of 800,
 * her feet on the desk at y 245 of 478 — with the Persian fitted to that
 * width.
 */
const CAT = { left: "70.75%", top: "26.6%", width: "19.6%" };

export function DeskScene({ className }: { className?: string }) {
  return (
    <div className={className}>
      <div className="relative">
        {/* eslint-disable-next-line @next/next/no-img-element -- an SVG needs
            no optimisation, and next/image would only add a request. */}
        <img src="/artwork/desk-2018.svg" alt="" width={800} height={478} className="w-full" />
        <svg viewBox="0 0 64 48" aria-hidden className="absolute" style={CAT}>
          <CatShapes />
        </svg>
      </div>
    </div>
  );
}
