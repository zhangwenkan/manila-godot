"""Build the shipyard-only Izezia sprite locally; never overwrite the source."""
from pathlib import Path
import hashlib

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "worker/Izezia.png"
OUTPUT = Path(__file__).resolve().parent / "art/izezia_shipyard.png"


def build():
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    rgb = np.array(Image.open(SOURCE).convert("RGB"))
    low = rgb.min(axis=2)
    chroma = rgb.max(axis=2).astype(np.int16) - low.astype(np.int16)
    # The supplied image has a baked-in gray/white checkerboard. Keep the
    # connected dark/colored silhouette, not every gray pixel in the picture.
    candidate = ((chroma > 18) | (low < 185)).astype(np.uint8)
    _, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, 8)
    component = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    mask = (labels == component).astype(np.uint8)
    # Preserve small enclosed pale details. Exterior background and large
    # silhouette gaps remain transparent, rather than filling a convex hull.
    count, holes, hole_stats, _ = cv2.connectedComponentsWithStats(1 - mask, 8)
    height, width = mask.shape
    for index in range(1, count):
        x, y, w, h, area = hole_stats[index]
        if x > 0 and y > 0 and x + w < width and y + h < height and area <= 1024:
            mask[holes == index] = 1
    x, y, w, h, _ = stats[component]
    bounds = (int(x) - 16, int(y) - 16, int(x + w) + 16, int(y + h) + 16)
    rgba = np.dstack((rgb, mask * 255))
    rgba[mask == 0, :3] = 0
    cropped = Image.fromarray(rgba).crop(bounds)
    # A 2x texture for the 72-unit scene character, with no aspect stretching.
    sprite = cropped.resize((round(cropped.width * 144 / cropped.height), 144), Image.Resampling.NEAREST)
    alpha = np.array(sprite)[:, :, 3]
    assert set(np.unique(alpha)) == {0, 255}
    assert not alpha[0].any() and not alpha[-1].any()
    assert not alpha[:, 0].any() and not alpha[:, -1].any()
    assert 0.25 < float((alpha == 0).mean()) < 0.6
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sprite.save(OUTPUT)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
    print(f"IZEZIA_SPRITE size={sprite.size} crop={bounds} transparent={float((alpha == 0).mean()):.3f} source_sha256={source_hash}")


if __name__ == "__main__":
    build()
