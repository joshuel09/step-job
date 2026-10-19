"""Snap the original artwork to its own flat palette.

No lighting correction, no white balance: this is the file itself, so the only
thing to undo is the anti-aliasing along each edge.
"""
import sys

import numpy as np
from PIL import Image

src, out_dir, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
SCALE = 3  # the letters on the billboard are six pixels tall in the original;
# quantising throws away the anti-aliasing that makes them readable, so the
# picture is enlarged first and the trace scaled back down.
im = Image.open(src).convert("RGBA")
im = im.resize((im.width * SCALE, im.height * SCALE), Image.LANCZOS)
a = np.asarray(im).astype(np.float32)
rgb, alpha = a[..., :3], a[..., 3]

# Transparency is the only background. White is a colour this artwork draws
# with — her teeth, her collar, the cup, the clock face — and treating it as
# background punched holes that are invisible on a white page and look like a
# scream on a dark one.
background = alpha < 128
fg = ~background
print("background", f"{background.mean() * 100:.1f}%", "| drawn pixels", int(fg.sum()))

pix = rgb[fg]
sample = pix[:: max(1, len(pix) // 80000)]
seed = np.asarray(
    Image.fromarray(sample.astype(np.uint8)[None, :, :])
    .convert("P", palette=Image.ADAPTIVE, colors=k)
    .convert("RGB")
).reshape(-1, 3)
centres = np.unique(seed, axis=0).astype(np.float32)[:k]
for _ in range(16):
    d = ((sample[:, None, :] - centres[None, :, :]) ** 2).sum(2)
    lab = d.argmin(1)
    for i in range(len(centres)):
        m = lab == i
        if m.any():
            centres[i] = sample[m].mean(0)

d = ((pix[:, None, :] - centres[None, :, :]) ** 2).sum(2)
labels = np.full(rgb.shape[:2], 255, dtype=np.uint8)
labels[fg] = d.argmin(1).astype(np.uint8)
np.save(f"{out_dir}/labels.npy", labels)
np.save(f"{out_dir}/centres.npy", centres)

out = np.full(a.shape[:2] + (3,), 255, dtype=np.uint8)
out[fg] = centres.astype(np.uint8)[labels[fg]]
Image.fromarray(out).save(f"{out_dir}/quantised.png")
for i, c in enumerate(centres.astype(int)):
    print(f"{i:2d} #{c[0]:02x}{c[1]:02x}{c[2]:02x}  {(labels == i).mean() * 100:5.2f}%")
