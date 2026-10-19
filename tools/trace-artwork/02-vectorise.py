"""Trace the original artwork, leaving the cat out.

The source is the artwork file itself, so there is nothing to undo but the
anti-aliasing: no lighting correction, no white balance, no smoothing, and no
shapes drawn by hand to cover for a blurry photograph.
"""
import sys

import numpy as np
import potrace
from PIL import Image

out_dir, src = sys.argv[1], sys.argv[2]
lab = np.load(f"{out_dir}/labels.npy")
SCALE = 3  # the labels were made from a 3x copy; the trace scales back down
src_im = Image.open(src).convert("RGB")
rgb = np.asarray(src_im.resize((src_im.width * SCALE, src_im.height * SCALE), Image.LANCZOS))
H, W = lab.shape

# The cat, by the corner she occupies rather than by colour: her brown is also
# the chair and the heart on the cup.
CAT_REGION = tuple(v * SCALE for v in (566, 150, 740, 246))  # stop at the desk edge
cx0, cy0, cx1, cy1 = CAT_REGION
cat = np.zeros_like(lab, dtype=bool)
cat[cy0:cy1, cx0:cx1] = lab[cy0:cy1, cx0:cx1] != 255
ys, xs = np.nonzero(cat)
print("cat", xs.min(), ys.min(), xs.max(), ys.max())
lab[cy0:cy1, cx0:cx1] = 255  # the Persian is drawn over the gap


def colour_of(cluster: int) -> str:
    """The exact colour the artwork uses most often in this cluster."""
    pixels = rgb[lab == cluster]
    values, counts = np.unique(pixels, axis=0, return_counts=True)
    r, g, b = values[counts.argmax()]
    return f"#{r:02x}{g:02x}{b:02x}"


def to_path(mask: np.ndarray) -> str:
    bmp = potrace.Bitmap(~mask)  # potracer treats zero as ink
    path = bmp.trace(turdsize=40, alphamax=1.0, opticurve=True, opttolerance=1.0)

    def pt(p):
        return f"{p.x / SCALE:.1f} {p.y / SCALE:.1f}"

    out = []
    for curve in path:
        out.append(f"M{pt(curve.start_point)}")
        for seg in curve:
            if seg.is_corner:
                out.append(f"L{pt(seg.c)}L{pt(seg.end_point)}")
            else:
                out.append(f"C{pt(seg.c1)} {pt(seg.c2)} {pt(seg.end_point)}")
        out.append("Z")
    return "".join(out)


layers = []
for cluster in range(int(lab[lab != 255].max()) + 1):
    mask = lab == cluster
    if mask.sum() < 300:
        continue
    layers.append((mask.sum(), colour_of(cluster), to_path(mask)))

layers.sort(key=lambda layer: -layer[0])
body = "\n".join(f'  <path fill="{c}" d="{d}"/>' for _, c, d in layers)
svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W // SCALE} {H // SCALE}">\n'
    f'{body}\n</svg>\n'
)
open(f"{out_dir}/artwork.svg", "w").write(svg)
print(f"{len(layers)} layers, {len(svg) / 1024:.0f} KB")
