"""Correct the photograph without flattening its colour."""
import sys

import numpy as np
from PIL import Image, ImageFilter

src, out_dir = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
a = np.asarray(im).astype(np.float32)

# Crop to the blue card.
b_dom = (a[..., 2] > a[..., 0] + 25) & (a[..., 2] > 90)
ys, xs = np.nonzero(b_dom)
a = a[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
print("cropped to", a.shape[1], "x", a.shape[0])

# 1. Even the brightness, but only the brightness: divide luminance by a heavy
#    blur of itself. Dividing all three channels is what washed the colour out.
lum = a.mean(2)
blur = np.asarray(
    Image.fromarray(lum.astype(np.uint8)).filter(ImageFilter.GaussianBlur(140))
).astype(np.float32)
a = a * (lum.mean() / np.maximum(blur, 1))[..., None]

# 2. White balance against the brightest neutral pixels, which in this
#    drawing are the window frame and the valance. Picking a patch by hand got
#    the blue card instead and turned the whole thing orange.
lum2 = a.mean(2)
bright = lum2 > np.percentile(lum2, 99)
ref = a[bright].mean(0)
gain = np.clip(ref.max() / np.maximum(ref, 1), 1.0, 1.35)
a = a * gain
print("white reference", ref.round(1), "gain", gain.round(3))

a = np.clip(a, 0, 255)

# 3. Lift saturation back to where flat artwork sits.
grey = a.mean(2, keepdims=True)
a = np.clip(grey + (a - grey) * 1.25, 0, 255).astype(np.uint8)

out = Image.fromarray(a).filter(ImageFilter.MedianFilter(5))
out.save(f"{out_dir}/corrected.png")
out.resize((out.width // 2, out.height // 2)).save(f"{out_dir}/corrected_small.png")
print("saved corrected.png")
