"""Trace the quantised artwork into an SVG, leaving the cat out."""
import sys

import numpy as np
import potrace
from PIL import Image, ImageFilter

out_dir = sys.argv[1]
W_OUT, H_OUT = 1040, 640

lab_full = np.load(f"{out_dir}/labels.npy")

# Cluster -> the colour the artwork paints it.
COLOUR = {
    0: "#1b1b19",   # shoes, the darkest of the suit
    1: "#232320",   # suit
    2: "#3b2314",   # hair
    3: "#4f4b46",   # building shadow, desk underside
    4: "#5c574f",   # dark buildings
    5: "#6f6a63",   # mid buildings
    6: "#7b746b",   # drawer unit
    7: "#8a8f88",   # desk top
    9: "#a9b4bb",   # glass, laptop lid
    10: "#d9503a",  # chair, clock rim, the heart
    11: "#d9c843",  # the billboard's shaded edge
    12: "#b8c2c8",  # lighter glass
    13: "#c8d1d6",  # lit windows
    14: "#e4cf3f",  # the billboard
    15: "#d9e2e7",  # pale grey
    16: "#f3cd9f",  # skin
    17: "#f4f8f8",  # white: the frame, the cup, the clock face
    18: "#3aa9c9",  # STEP, which the artwork letters in blue
}
CAT = 8  # left out; the Persian is drawn over the gap
CAT_REGION = (1470, 420, 1870, 700)
BILLBOARD = (380, 230, 1420, 480)  # where cluster 9 is lettering, not glass


def fill_holes(mask: np.ndarray) -> np.ndarray:
    """A silhouette, not an outline: flood from the border and invert."""
    h, w = mask.shape
    out = np.zeros((h + 2, w + 2), dtype=bool)
    out[1:-1, 1:-1] = mask
    im = Image.fromarray((~out * 255).astype(np.uint8))
    from collections import deque

    seen = np.zeros_like(out)
    arr = np.asarray(im) > 127
    q = deque([(0, 0)])
    seen[0, 0] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h + 2 and 0 <= nx < w + 2 and not seen[ny, nx] and arr[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    return (~seen[1:-1, 1:-1]) | mask


# The cat: her tan appears elsewhere, so take the cluster only in her corner,
# grow it, and fill it, so her stripes go with her rather than being left
# floating on the desk.
x0, y0, x1, y1 = CAT_REGION
cat = np.zeros_like(lab_full, dtype=bool)
cat[y0:y1, x0:x1] = lab_full[y0:y1, x0:x1] == CAT
cat = np.asarray(
    Image.fromarray((cat * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(13))
) > 127
cat[y0:y1, x0:x1] = fill_holes(cat[y0:y1, x0:x1])
desk_top = int(np.nonzero(lab_full[400:, 1600] == 7)[0].min() + 400)
rows = np.arange(lab_full.shape[0])[:, None]
lab_full[cat & (rows < desk_top)] = 255      # sky behind her
lab_full[cat & (rows >= desk_top)] = 7       # desk under her

# Her outline and the tip of her tail are not her tan, so clearing the tan
# left them floating. Everything in the corner she occupies goes with her.
corner = np.zeros_like(lab_full, dtype=bool)
corner[415:desk_top, 1500:1895] = True
lab_full[corner] = 255
print("cat removed; desk top at", desk_top)

# The photograph's bezel at the corners: keep only what is inside the card.
yy, xx = np.mgrid[0 : lab_full.shape[0], 0 : lab_full.shape[1]]
h, w = lab_full.shape
r, inset = 104, 10
inside = (
    (xx >= inset) & (xx < w - inset) & (yy >= inset) & (yy < h - inset)
)
for cx, cy, sx, sy in (
    (inset + r, inset + r, -1, -1),
    (w - inset - r, inset + r, 1, -1),
    (inset + r, h - inset - r, -1, 1),
    (w - inset - r, h - inset - r, 1, 1),
):
    past = ((xx - cx) * sx > 0) & ((yy - cy) * sy > 0)
    inside &= ~(past & ((xx - cx) ** 2 + (yy - cy) ** 2 > r * r))
lab_full[~inside] = 255

# The photograph's glare: light blobs past the desk's right leg.
glare = np.zeros_like(lab_full, dtype=bool)
glare[:, 1880:] = True
lab_full[glare & np.isin(lab_full, [9, 12, 13, 15, 17])] = 255

# STEP is lettered in blue on the billboard; the same cluster is glass elsewhere.
bx0, by0, bx1, by1 = BILLBOARD
region = np.zeros_like(lab_full, dtype=bool)
region[by0:by1, bx0:bx1] = True
lab_full[region & (lab_full == 9)] = 18

# Traced at full resolution. Half resolution plus an open/close smoothed the
# grain away and the laptop with it — the drawing's own edges are only a few
# pixels wide in the photograph.
lab = lab_full
H, W = lab.shape
scale = W_OUT / W


def clean(mask: np.ndarray) -> np.ndarray:
    """Take the speckle off, and nothing else."""
    im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.ModeFilter(5))
    return np.asarray(im) > 127


def to_path(mask: np.ndarray) -> str:
    bmp = potrace.Bitmap(~mask)  # potracer treats zero as ink, so invert
    path = bmp.trace(turdsize=140, alphamax=1.0, opticurve=True, opttolerance=0.8)

    def pt(p):
        return f"{p.x * scale:.1f} {p.y * scale:.1f}"

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
for cluster, colour in COLOUR.items():
    mask = clean(lab == cluster)
    if mask.sum() < 500:
        continue
    d = to_path(mask)
    if d:
        layers.append((mask.sum(), colour, d))

layers.sort(key=lambda layer: -layer[0])
body = "\n".join(f'  <path fill="{c}" d="{d}"/>' for _, c, d in layers)
svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_OUT} {H_OUT}">\n'
    f'  <defs><clipPath id="card">'
    f'<rect width="{W_OUT}" height="{H_OUT}" rx="26"/></clipPath></defs>\n'
    f'  <g clip-path="url(#card)">\n'
    f'  <rect width="{W_OUT}" height="{H_OUT}" fill="#3fb0dc"/>\n{body}\n  </g>\n</svg>\n'
)
open(f"{out_dir}/artwork.svg", "w").write(svg)
print(f"{len(layers)} layers, {len(svg) / 1024:.0f} KB")
