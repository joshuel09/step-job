import { BrandMark } from "@/components/brand/footsteps";

/**
 * STEP in blue, JOB in charcoal — the 2018 lockup, set in the interface's own
 * typeface instead of the original's rounded display face.
 *
 * The brand name is not translated, so this is the one piece of text on the
 * page that is the same in both locales.
 */
export function Wordmark({
  size = "sm",
  compact = false,
}: {
  size?: "sm" | "lg";
  /** Tile only on a narrow screen, where the name costs a navigation item. */
  compact?: boolean;
}) {
  const large = size === "lg";

  return (
    <span className="inline-flex items-center gap-2">
      <BrandMark className={large ? "h-11 w-11" : "h-7 w-7"} />
      <span
        className={`font-semibold tracking-tight ${large ? "text-3xl" : "text-base"} ${
          compact ? "hidden sm:inline" : ""
        }`}
        // One accessible name for the two differently coloured halves.
        aria-label="Step Job"
      >
        <span className="bg-gradient-to-br from-brand-400 to-brand-600 bg-clip-text text-transparent">
          STEP
        </span>
        <span className="ml-[0.06em] text-ink dark:text-brand-50">JOB</span>
      </span>
    </span>
  );
}
