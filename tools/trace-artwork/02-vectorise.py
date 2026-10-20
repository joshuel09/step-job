"""Trace the original artwork into a base and the parts that move.

The banner is one flat picture, so nothing in it can move on its own. The
parts that should — her head, her forearm, each shin, and the cat — are cut
out of the base here and written as their own files on the same 800 x 478
grid, so the page can stack them and animate each about its own joint.
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

# Her joints, in the artwork's own coordinates. Each part is the box that
# moves and the point it turns about.
# For each part: the box it is cut into, the box the base loses, and the joint
# it turns about.
#
# The two boxes differ on purpose. The part reaches past its joint into the
# limb above it, while the base keeps that stretch — so those pixels exist in
# both, and when the part turns, its overlap slides over identical pixels
# underneath. The overlap is always inside a solid black area, where sliding
# is invisible. Cut them to the same box and every rotation tears a gap at
# the joint.
PARTS = {
    "head": ((466, 18, 608, 246), (466, 18, 608, 214), (528, 214)),
    # The typing arm stops short of the mug: her other hand is holding it, and
    # an arm that takes the mug with it is the arm coming apart.
    "arm": ((412, 216, 516, 252), (412, 216, 508, 252), (508, 234)),
    # The mug is lifted out too, though it never moves. It is drawn after the
    # arm, so it covers the arm's cut edge — the one place that edge would
    # otherwise show.
    "mug": ((498, 206, 556, 252), (498, 206, 556, 252), (0, 0)),
    # Whole legs, from the hip. A foot alone moved like a puppet's, and a
    # shin alone tore a hole where the chair should carry on behind it.
    #
    # They separate by colour: the artwork paints the near leg #262626 and the
    # far one pure black. Below the desk's underside that is unambiguous, and
    # it means neither box has to guess where one leg ends and the other
    # begins where they cross.
}

# The mug is not hers, so it is cut whole rather than narrowed to her colours.
WHOLE = {"mug"}
# Her shoes are cut by what they are not, rather than by her colours: the
# anti-aliased pixels between a black shoe and a skin ankle match neither,
# and leaving them behind made the ankle look perforated.
ANYTHING_BUT_THE_ROOM = {"shoe-near", "shoe-far"}


def scaled(box):
    return tuple(v * SCALE for v in box)


def colour_of(mask: np.ndarray, cluster: int) -> str:
    """The exact colour the artwork uses most often here."""
    pixels = rgb[mask & (lab == cluster)]
    values, counts = np.unique(pixels, axis=0, return_counts=True)
    r, g, b = values[counts.argmax()]
    return f"#{r:02x}{g:02x}{b:02x}"


def to_path(mask: np.ndarray, turdsize: int = 40) -> str:
    bmp = potrace.Bitmap(~mask)  # potracer treats zero as ink
    path = bmp.trace(turdsize=turdsize, alphamax=1.0, opticurve=True, opttolerance=1.0)

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


def write(name: str, within: np.ndarray, turdsize: int = 40, under: str = "") -> None:
    layers = []
    for cluster in range(int(lab[lab != 255].max()) + 1):
        mask = (lab == cluster) & within
        if mask.sum() < 300:
            continue
        layers.append((mask.sum(), colour_of(within, cluster), to_path(mask, turdsize)))
    layers.sort(key=lambda layer: -layer[0])
    body = under + "\n".join(f'  <path fill="{c}" d="{d}"/>' for _, c, d in layers)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W // SCALE} {H // SCALE}">\n'
        f"{body}\n</svg>\n"
    )
    open(f"{out_dir}/{name}.svg", "w").write(svg)
    print(f"{name}: {len(layers)} layers, {len(svg) / 1024:.0f} KB")


# --- the cat ---------------------------------------------------------------
#
# Everything the tabby occupies goes, except the desk she lies on and the
# chair behind her. The cut starts at x 605, to the right of Mich's shoulder:
# the tabby's head overlaps that shoulder, and cutting through it either took
# a bite out of Mich or had to invent the shoulder back. It does not need
# inventing — the Persian is wider than the tabby and covers the sliver that
# is left.
r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
desk = (abs(r - g) < 14) & (abs(g - b) < 14) & (r > 85) & (r < 200)
chair = (r > 140) & (g < 110) & (b < 110) & (abs(g - b) < 30)

box = np.zeros(lab.shape, bool)
bx0, by0, bx1, by1 = scaled((605, 158, 748, 243))
box[by0:by1, bx0:bx1] = True
lab[box & ~desk & ~chair] = 255

# Only she moves. A box around her knee also contains the chair, and a box
# around her forearm also contains the laptop, so each part is the box
# narrowed to her own colours: hair, skin, the black of her suit, and the
# white of her collar — the last only where the collar is, since white is
# also the chair's legs and the cup.
white = rgb.min(2) > 225
hair = (abs(r - 0x50) < 46) & (abs(g - 0x24) < 42) & (b < 60)
skin = (abs(r - 0xF7) < 26) & (abs(g - 0xC3) < 34) & (abs(b - 0x9F) < 40)
black = rgb.max(2) < 72
# White is hers in two places and nowhere else: her collar, and her teeth.
# Everywhere else it is the chair's legs, the mug or the window frame — which
# is why it cannot simply be added to the list.
her_white = np.zeros(lab.shape, bool)
for box in ((488, 160, 566, 212), (494, 110, 542, 148)):
    wx0, wy0, wx1, wy1 = scaled(box)
    her_white[wy0:wy1, wx0:wx1] = white[wy0:wy1, wx0:wx1]
her = hair | skin | black | her_white

# --- the parts that move ---------------------------------------------------
movable = (lab != 255) & ~desk & ~chair & ~white

CUSTOM: dict[str, np.ndarray] = {}

part_masks, holes = {}, {}
for name, (part_box, hole_box, _) in PARTS.items():
    if name in CUSTOM:
        part_masks[name] = CUSTOM[name]
        continue

    if name in WHOLE:
        keep = np.ones(lab.shape, bool)
    elif name in ANYTHING_BUT_THE_ROOM:
        keep = (lab != 255) & ~desk & ~chair & ~white
    else:
        keep = her
    px0, py0, px1, py1 = scaled(part_box)
    m = np.zeros(lab.shape, bool)
    m[py0:py1, px0:px1] = True
    part_masks[name] = m & keep

    if name in WHOLE:
        # Only the mug is lifted out of the base, so that it can be drawn
        # after the arm and cover the arm's own edge.
        hx0, hy0, hx1, hy1 = scaled(hole_box)
        h = np.zeros(lab.shape, bool)
        h[hy0:hy1, hx0:hx1] = True
        holes[name] = h & keep

# Nothing is cut out of the base except the mug.
#
# Cutting a limb out leaves a hole, and behind a limb the artwork drew
# nothing — so the hole shows the page through it, which on a dark page is a
# black gash. Laying a copy of the limb over the top instead means there is
# never a hole: at rest the copy sits exactly on the original, and when it
# turns, the few pixels that peek out from under it are the same black as the
# limb itself. A fraction thicker, rather than torn.
moving = np.zeros(lab.shape, bool)
for h in holes.values():
    moving |= h

write("desk-2018", ~moving)
for name, m in part_masks.items():
    # A smaller speck limit on the parts: at 40 the trace dropped the slivers
    # along a cut and the ankle came out perforated.
    write(f"desk-2018-{name}", m, turdsize=8)

print("pivots:")
for name, (_, _, (px, py)) in PARTS.items():
    print(f"  {name}: {px / 800 * 100:.2f}% {py / 478 * 100:.2f}%")
