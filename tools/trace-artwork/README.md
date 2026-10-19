# Tracing the 2018 artwork

`apps/web/public/artwork/desk-2018.svg` is the 2018 Android banner, traced
from the artwork file itself (`stepjobbanner.png`, 800 × 478, flat colour on
transparency).

```bash
uv run --with numpy --with pillow python -I 01-quantise.py <banner.png> <work-dir> 20
uv run --with numpy --with potracer python -I 02-vectorise.py <work-dir> <banner.png>
```

1. **Quantise** — enlarge the banner 3×, then snap every pixel to one of 20
   flat colours. The enlargement is for the billboard: its letters are six
   pixels tall in the original, and quantising throws away the anti-aliasing
   that makes them readable, so there has to be more to quantise. Pixels that
   are transparent, or white where the file was flattened, are background.
2. **Vectorise** — trace each colour with potrace and scale the result back
   down. Fills are the exact colour the artwork uses most in that cluster, not
   a cluster average, so nothing drifts.

The cat is cut out by the corner she occupies rather than by colour — her
brown is also the chair and the heart on the cup — and the cut stops at the
desk's edge so the desk stays whole. The Persian is drawn over the gap by
`components/brand/scene.tsx`.

Two things worth keeping in mind if this is ever re-run:

- **potracer reads zero as ink.** `potrace.Bitmap(~mask)`, not `Bitmap(mask)`,
  or every layer traces the complement.
- **Cluster count matters more than it looks.** At 16 the artwork's two dark
  tones (`#262626` trousers, `#502400` hair) merged and she ended up with one
  brown leg. 20 separates them.

An earlier version of this pipeline traced a *photograph* of the app running
on a phone, and needed two more steps to undo the camera — lighting, white
balance — plus hand-drawn geometry over the window, where the grain made the
trace unusable. None of that is needed now. It is in the history if the
situation ever recurs.
