# Tracing the 2018 artwork

`apps/web/public/artwork/desk-2018.svg` is not drawn by hand. It is the 2018
Android home header, traced from a photograph of the app running on a phone,
so that the illustration on the landing page is the original artwork rather
than an imitation of it.

Three steps, run with `uv` so nothing is added to the web toolchain:

```bash
uv run --with numpy --with pillow python -I 01-correct.py <photo> <work-dir>
uv run --with numpy --with pillow python -I 02-quantise.py <work-dir>/corrected.png <work-dir> 18
uv run --with numpy --with potracer python -I 03-vectorise.py <work-dir>
```

1. **Correct** — crop to the blue card, even out the lighting by dividing the
   luminance (not the colour) by a heavy blur of itself, white balance against
   the brightest neutral pixels, and lift saturation back to where flat
   artwork sits.
2. **Quantise** — mask the card, then k-means the drawing into 18 flat
   colours. The card has to come out first or the clusters are spent on its
   gradient.
3. **Vectorise** — map each cluster to the colour the artwork paints it, trace
   each one with potrace, and assemble them largest-first.

The third step also does three things that are specific to this picture:

- **The cat is removed.** Her tan is taken only from the corner she occupies,
  grown and hole-filled so her stripes go with her, and what is behind her is
  filled in — sky above the desk line, desk below it. The Persian is drawn
  over the gap by the component.
- **The photograph's glare and bezel are removed** — light blobs past the
  desk's right leg, and everything outside the card's rounded corners.
- **STEP is recoloured blue** inside the billboard, where the cluster that
  letters it is the same one that paints the window glass.

If the original artwork file ever turns up, use that instead: a trace of a
photograph carries the camera's noise, and the tagline under STEP JOB is
already past the point where it reads as letters.
