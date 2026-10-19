"""Trace the quantised artwork into an SVG, leaving the cat out."""
import sys

import numpy as np
import potrace
from PIL import Image, ImageFilter

out_dir = sys.argv[1]
W_OUT, H_OUT = 1040, 640

lab_full = np.load(f"{out_dir}/labels.npy")
corrected = np.asarray(Image.open(f"{out_dir}/corrected.png").convert("RGB")).astype(np.float32)

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
BILLBOARD = (224, 170, 812, 420)  # the ellipse itself: wider, and it
# recoloured her eye blue


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


# Her eyes and brows are a few dark pixels each, and the camera's blur put
# them in with the window glass. Take them back by luminance, inside her face.
FACE = (1195, 170, 1420, 420)
fx0, fy0, fx1, fy1 = FACE
face = np.zeros_like(lab_full, dtype=bool)
face[fy0:fy1, fx0:fx1] = True
lab_full[face & (corrected.mean(2) < 105)] = 2

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

# The window and the laptop are not traced at all.
#
# They are the one part of this picture made of rectangles, an ellipse and a
# grid: shapes a photograph traces badly — every edge carries the camera's
# grain, and four near-identical greys fight along each one — and shapes that
# draw exactly. So they are cut out here and drawn as geometry underneath,
# while everything with a shape worth tracing (her, the chair, the desk, the
# drawers, the clock) stays traced.
#
# Her, the desk and the drawers cross the window, so only the window's own
# colours are cut: greys, white, yellow. The clusters that make up the desk
# and the figure stay.
# Above the desk, and to the left of the drawer unit below it, nothing is
# traced: that is all window, and the geometry underneath draws it. Keeping
# any cluster here let the photograph's ragged buildings and a ghost of the
# billboard's own lettering paint over the clean shapes.
#
# The laptop goes too, but its box stops short of her hand.
# The desk and the drawer unit are rectangles as well, and traced they came
# out with a wobbling edge. Their clusters only describe the desk now that the
# window is cut, so they go entirely and are drawn below.
# Everything grey is either the window or the desk, and both are drawn now.
# What stays traced is what cannot be described with a rectangle: her, the
# chair, the cup, the clock face.
TRACED = [0, 1, 2, 10, 16, 17]  # dark, hair, red, skin, white
lab_full[~np.isin(lab_full, TRACED + [255])] = 255

for rx0, ry0, rx1, ry1 in (
    (112, 56, 916, 660),     # the window, above the desk
    (112, 660, 588, 992),    # the window, left of the drawer unit
    (686, 392, 1120, 734),   # the laptop, stopping before her cuff
    (1570, 130, 1840, 400),  # the clock, which is drawn over the top
):
    lab_full[ry0:ry1, rx0:rx1] = 255

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


def clean(mask: np.ndarray, radius: float = 4) -> np.ndarray:
    """Smooth the boundary without losing anything that is actually drawn.

    Blur the mask and threshold it back. A wiggle of a few pixels — which is
    all the camera's grain is — blurs below half and disappears; a shape ten
    pixels across survives, because most of its area is still above half.
    Morphology ate the laptop; this does not.
    """
    im = Image.fromarray((mask * 255).astype(np.uint8))
    im = im.filter(ImageFilter.ModeFilter(5)).filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(im) > 127


def to_path(mask: np.ndarray, noisy: bool = False) -> str:
    bmp = potrace.Bitmap(~mask)  # potracer treats zero as ink, so invert
    path = bmp.trace(
        turdsize=260, alphamax=1.3, opticurve=True, opttolerance=1.4
    )

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
# The pale clusters are the window glass and the glare on it, where the
# photograph is noisiest and the drawing has the least detail to lose.
NOISY: set[int] = set()

for cluster, colour in COLOUR.items():
    mask = clean(lab == cluster, radius=4)
    if mask.sum() < 500:
        continue
    d = to_path(mask, noisy=cluster in NOISY)
    if d:
        layers.append((mask.sum(), colour, d))

layers.sort(key=lambda layer: -layer[0])
def windows_grid(x, y, cols, rows, gap, w, h):
    return "".join(
        f'<rect x="{x + c * gap}" y="{y + r * gap}" width="{w}" height="{h}" rx="1"/>'
        for r in range(rows)
        for c in range(cols)
    )


# Drawn, not traced: the window, the skyline, the billboard and the laptop.
GEOMETRY = f"""  <g>
    <rect x="68" y="60" width="388" height="432" fill="#eeefe9"/>
    <rect x="86" y="96" width="352" height="378" fill="#b6b9bb"/>
    <g clip-path="url(#pane)">
      <g fill="#c9cccd" opacity="0.5">
        <ellipse cx="150" cy="126" rx="42" ry="26"/>
        <ellipse cx="236" cy="112" rx="52" ry="30"/>
        <ellipse cx="330" cy="130" rx="46" ry="26"/>
      </g>
      <rect x="96" y="226" width="74" height="26" fill="#6f6a63"/>
      <g fill="#6f6a63">
        <rect x="90" y="252" width="118" height="222"/>
        <rect x="288" y="238" width="86" height="236"/>
      </g>
      <g fill="#4f4b48">
        <rect x="208" y="268" width="80" height="206"/>
        <rect x="374" y="262" width="64" height="212"/>
      </g>
      <rect x="196" y="286" width="64" height="40" fill="#b6b9bb"/>
      <g fill="#c8d1d6">
        {windows_grid(104, 282, 3, 5, 26, 14, 20)}
        {windows_grid(216, 300, 4, 6, 17, 9, 11)}
        {windows_grid(298, 266, 3, 7, 22, 12, 14)}
        {windows_grid(384, 292, 3, 6, 17, 9, 11)}
      </g>
      <rect x="252" y="236" width="10" height="36" fill="#59544f"/>
      <path d="M196 212h124l-14 28H210z" fill="#59544f"/>
      <g fill="#e4cf3f">
        <circle cx="224" cy="226" r="8"/>
        <circle cx="258" cy="226" r="8"/>
        <circle cx="292" cy="226" r="8"/>
      </g>
      <ellipse cx="258" cy="162" rx="146" ry="70" fill="#e4cf3f"/>
      <text x="258" y="166" text-anchor="middle" font-size="54" font-weight="800"
            letter-spacing="1" fill="#1f1d1a"
            font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif"
      ><tspan fill="#2a93c7">STEP</tspan> JOB</text>
      <text x="258" y="196" text-anchor="middle" font-size="16" font-weight="700"
            letter-spacing="0.6" fill="#1f1d1a"
            font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif"
      >BOOST YOUR CONFIDENCE</text>
      <path d="M86 96h150L86 330z" fill="#c9cccd" opacity="0.38"/>
      <path d="M306 96h132v58L166 474h-80z" fill="#c9cccd" opacity="0.2"/>
    </g>
    <rect x="62" y="40" width="400" height="34" rx="3" fill="#eeefe9"/>
    <rect x="285" y="346" width="660" height="24" rx="3" fill="#8a8f88"/>
    <rect x="285" y="366" width="660" height="12" rx="3" fill="#615c57"/>
    <rect x="903" y="376" width="22" height="236" rx="4" fill="#7b746b"/>
    <rect x="292" y="376" width="179" height="252" rx="4" fill="#7b746b"/>
    <g fill="#615c57">
      <rect x="292" y="458" width="179" height="4"/>
      <rect x="292" y="540" width="179" height="4"/>
    </g>
    <g fill="#eeefe9">
      <rect x="359" y="422" width="46" height="9" rx="4"/>
      <rect x="359" y="504" width="46" height="9" rx="4"/>
      <rect x="359" y="586" width="46" height="9" rx="4"/>
    </g>
    <path d="M392 228h170l26 122H358z" fill="#c8c6c2"/>
    <path d="M474 282l15 9v18l-15 9-15-9v-18z" fill="#a9a7a3" opacity="0.6"/>
    <path d="M350 350h248l12 16H338z" fill="#a9a7a3"/>
  </g>
"""

# Drawn over the trace: the clock is a ring, a face and two hands, and the
# camera lost the hands in the glare off the glass.
CLOCK = """  <g>
    <circle cx="851" cy="131" r="52" fill="#d9503a"/>
    <circle cx="851" cy="131" r="43" fill="#f4f8f8"/>
    <path d="M851 98v33l24 14" fill="none" stroke="#2b2a27" stroke-width="4"
          stroke-linecap="round"/>
  </g>
"""

body = GEOMETRY + "\n".join(f'  <path fill="{c}" d="{d}"/>' for _, c, d in layers)
svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_OUT} {H_OUT}">\n'
    f'  <defs>'
    f'<clipPath id="card"><rect width="{W_OUT}" height="{H_OUT}" rx="26"/></clipPath>'
    f'<clipPath id="pane"><rect x="86" y="96" width="352" height="378"/></clipPath>'
    f'</defs>\n'
    f'  <g clip-path="url(#card)">\n'
    f'  <rect width="{W_OUT}" height="{H_OUT}" fill="#3fb0dc"/>\n{body}\n{CLOCK}  </g>\n'
    f'</svg>\n'
)
open(f"{out_dir}/artwork.svg", "w").write(svg)
print(f"{len(layers)} layers, {len(svg) / 1024:.0f} KB")
