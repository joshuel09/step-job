"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { WorldArt } from "@/components/landing/world-art";
import { HOTSPOTS, WORLD_H, WORLD_W, type HotspotKey } from "@/lib/site";

/**
 * The landing page's illustration, and the one thing on it you can do.
 *
 * Each marker sits on the part of the drawing it describes — the roof sign,
 * a floor of the building, the pair out front — and opens a card next to
 * itself when the pointer reaches it. A marker is still a button, not a
 * decoration: a tap opens it where there is no pointer, it takes focus, and
 * Escape or a click elsewhere closes it.
 *
 * The markers are positioned as percentages of the artwork's own grid, so
 * they stay on their subject at every width without being inside the SVG,
 * where they could not be buttons.
 */
export function World({ locale }: { locale: string }) {
  const t = useTranslations("world");
  const [open, setOpen] = useState<HotspotKey | null>(null);
  const frame = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(null);
    const onClick = (event: MouseEvent) => {
      if (!frame.current?.contains(event.target as Node)) setOpen(null);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  // The card sits a few pixels off the marker, so a pointer travelling from
  // one to the other crosses a gap. Closing on a short delay lets it arrive;
  // closing immediately would shut the card on the way to its link.
  const leaving = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(leaving.current), []);

  const show = useCallback((key: HotspotKey) => {
    clearTimeout(leaving.current);
    setOpen(key);
  }, []);

  const hide = useCallback(() => {
    clearTimeout(leaving.current);
    leaving.current = setTimeout(() => setOpen(null), 160);
  }, []);

  return (
    <div ref={frame} className="relative w-full">
      <svg
        viewBox={`0 0 ${WORLD_W} ${WORLD_H}`}
        className="block w-full"
        role="presentation"
        aria-hidden
      >
        <WorldArt />
      </svg>

      {HOTSPOTS.map(({ key, x, y, href, side, up }) => {
        const showing = open === key;
        return (
          <div
            key={key}
            // Below sm the drawing is a 200px band: a 32px marker covers the
            // thing it points at and the card it opens covers the drawing.
            // Everything a marker offers is also a card further down the page.
            className="absolute hidden sm:block"
            style={{ left: `${(x / WORLD_W) * 100}%`, top: `${(y / WORLD_H) * 100}%` }}
            onMouseEnter={() => show(key)}
            onMouseLeave={hide}
          >
            <button
              type="button"
              // Opens, never toggles: with a mouse the pointer has already
              // opened it on the way in, so a toggle would shut the card the
              // moment you clicked the thing you were reading about. Touch
              // has no hover, so there the click is what opens it.
              onClick={() => show(key)}
              onFocus={() => show(key)}
              onBlur={hide}
              aria-expanded={showing}
              aria-label={t(`${key}.title`)}
              className={`marker ${showing ? "marker-open" : ""}`}
            >
              <span aria-hidden>i</span>
            </button>

            {showing ? (
              <div
                className={`world-card ${side === "left" ? "world-card-left" : ""} ${
                  up ? "world-card-up" : ""
                }`}
                role="dialog"
                aria-label={t(`${key}.title`)}
              >
                <h3 className="text-sm font-semibold">{t(`${key}.title`)}</h3>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">{t(`${key}.body`)}</p>
                {href ? (
                  <Link
                    href={`/${locale}/${href}`}
                    className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-warm"
                  >
                    {t("visit")}
                    <span aria-hidden>→</span>
                  </Link>
                ) : null}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
