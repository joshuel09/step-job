import type { ComponentType } from "react";

import type { AvailableKey } from "@/lib/site";

/**
 * One glyph per card, in place of the 2018 app's stock illustrations.
 *
 * Line drawings on purpose: the original tiles each carried a different
 * illustration in a different palette, which made the grid read as eight
 * products. These are one weight, one colour, inherited from the card.
 */

type GlyphProps = { className?: string };

function Frame({ className, children }: GlyphProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="presentation"
      aria-hidden
      className={className}
    >
      {children}
    </svg>
  );
}

/** The profile: a person on a card. */
function ProfileGlyph(props: GlyphProps) {
  return (
    <Frame {...props}>
      <rect x="3" y="4" width="18" height="16" rx="3" />
      <circle cx="9" cy="10.5" r="2.2" />
      <path d="M5.8 16.4c.6-1.7 1.8-2.6 3.2-2.6s2.6.9 3.2 2.6" />
      <path d="M15 9.5h3.5M15 13h3.5" />
    </Frame>
  );
}

/** Import: a document coming in. */
function ImportGlyph(props: GlyphProps) {
  return (
    <Frame {...props}>
      <path d="M14 3H7a2 2 0 0 0-2 2v7" />
      <path d="M14 3l5 5v11a2 2 0 0 1-2 2H9" />
      <path d="M14 3v5h5" />
      <path d="M3 16h7M7.5 12.5 11 16l-3.5 3.5" />
    </Frame>
  );
}

/** 履歴書: a document with the photo box the form always has. */
function RirekishoGlyph(props: GlyphProps) {
  return (
    <Frame {...props}>
      <rect x="4" y="3" width="16" height="18" rx="2.5" />
      <rect x="13.5" y="6" width="4" height="5" rx="1" />
      <path d="M6.8 6.5h4.2M6.8 9.5h4.2M6.8 13.5h10.4M6.8 16.5h10.4" />
    </Frame>
  );
}

/** Career stories: the longer account, in the user's own voice. */
function StoriesGlyph(props: GlyphProps) {
  return (
    <Frame {...props}>
      <path d="M20 13.5A3.5 3.5 0 0 1 16.5 17H9l-4 3v-3.4A3.5 3.5 0 0 1 4 13.5v-5A3.5 3.5 0 0 1 7.5 5h9A3.5 3.5 0 0 1 20 8.5z" />
      <path d="M8.5 9.5h7M8.5 12.5h4.5" />
    </Frame>
  );
}

export const GLYPHS: Record<AvailableKey, ComponentType<GlyphProps>> = {
  profile: ProfileGlyph,
  import: ImportGlyph,
  rirekisho: RirekishoGlyph,
  stories: StoriesGlyph,
};
