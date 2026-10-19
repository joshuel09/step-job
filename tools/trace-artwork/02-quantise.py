"""Separate the blue card, then quantise only what is drawn on it."""
import sys

import numpy as np
from PIL import Image, ImageFilter

src, out_dir, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
im = Image.open(src).convert("RGB")
a = np.asarray(im).astype(np.float32)
r, g, b = a[..., 0], a[..., 1], a[..., 2]

# The card: strongly blue, and brighter in blue than in red by a wide margin.
# Everything drawn on it — greys, black, skin, yellow, red — is not.
card = (b > r + 40) & (b > 110) & (g > r + 10)
card = np.asarray(
    Image.fromarray((card * 255).astype(np.uint8)).filter(ImageFilter.ModeFilter(9))
) > 127

fg = ~card
pix = a[fg]
print("card covers", f"{card.mean()*100:.1f}%", "| foreground pixels", len(pix))

sample = pix[:: max(1, len(pix) // 60000)]
seed = np.asarray(
    Image.fromarray(sample.astype(np.uint8)[None, :, :])
    .convert("P", palette=Image.ADAPTIVE, colors=k)
    .convert("RGB")
).reshape(-1, 3)
centres = np.unique(seed, axis=0).astype(np.float32)[:k]
for _ in range(14):
    d = ((sample[:, None, :] - centres[None, :, :]) ** 2).sum(2)
    lab = d.argmin(1)
    for i in range(len(centres)):
        m = lab == i
        if m.any():
            centres[i] = sample[m].mean(0)

d = ((pix[:, None, :] - centres[None, :, :]) ** 2).sum(2)
labels = np.full(a.shape[:2], 255, dtype=np.uint8)
labels[fg] = d.argmin(1).astype(np.uint8)
np.save(f"{out_dir}/labels.npy", labels)
np.save(f"{out_dir}/centres.npy", centres)

out = np.zeros_like(a, dtype=np.uint8)
out[card] = (63, 176, 220)
out[fg] = centres.astype(np.uint8)[labels[fg]]
Image.fromarray(out).save(f"{out_dir}/quantised.png")
for i, c in enumerate(centres.astype(int)):
    print(f"{i:2d} #{c[0]:02x}{c[1]:02x}{c[2]:02x}  {(labels == i).mean()*100:5.2f}%")
