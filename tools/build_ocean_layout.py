"""Rebuild the ocean's layout data; no painted water color is saved.

Run from any directory with Python, Pillow, NumPy and OpenCV installed:
    python tools/build_ocean_layout.py

R = water coverage, G = distance to a solid edge / 128,
B = distance to a sandy shore / 192, A = cast-shadow coverage.
The PNG is data, not an albedo texture. Keep its Godot import lossless.
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scene/image/scene.png"
OUTPUT = ROOT / "scene/image/ocean_layout.png"


def build_layout() -> None:
    source = np.asarray(Image.open(SOURCE).convert("RGB"))
    height, width = source.shape[:2]
    if (width, height) != (6144, 1152):
        raise ValueError("This coastline layout is authored for the 6144 x 1152 harbor.")
    red, green, blue = source.astype(np.int16).transpose(2, 0, 1)
    water_color = (blue - red > 24) & (green - red > 14) & (blue > green - 4)
    wet_foam = (red > 112) & (green >= red) & (blue >= red - 22) & (green - blue < 46)
    candidates = (water_color | wet_foam).astype(np.uint8)
    candidates[:496] = 0  # The sky is also blue, above the farthest sea inlet.

    # The blue cargo hull touches the sea and must not join the water component.
    hull = np.array([
        (52, 654), (212, 663), (383, 620), (387, 644), (306, 705),
        (255, 730), (219, 747), (198, 772), (117, 772), (91, 748), (67, 709),
    ], dtype=np.int32)
    cv2.fillPoly(candidates, [hull], 0)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidates, 8)
    water_label = labels[-1, width // 2]
    water = labels == water_label

    # Small pockets behind the wooden piers can be cut off by posts and ropes.
    near_water = cv2.dilate(water.astype(np.uint8), np.ones((31, 31), np.uint8)) != 0
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        if label == water_label or x < 3000 or area < 3 or area > 2000:
            continue
        component = labels[y:y + h, x:x + w] == label
        if np.any(near_water[y:y + h, x:x + w] & component):
            water[y:y + h, x:x + w] |= component

    # Close antialiasing pinholes without swallowing posts or ropes.
    count, holes, stats, _ = cv2.connectedComponentsWithStats((~water).astype(np.uint8), 8)
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        if area <= 48:
            region = water[y:y + h, x:x + w]
            region[holes[y:y + h, x:x + w] == label] = True

    coverage = water.astype(np.uint8)
    edge_distance = cv2.distanceTransform(coverage, cv2.DIST_L2, 5)
    sand = (red > 145) & (green > 112) & (red - green > 8) & (green - blue > 12)
    # Light wood can have the same hue as sand. Only sizeable connected sandy
    # regions seed the beach distance, otherwise foam forms rings around posts.
    sand_count, sand_labels, sand_stats, _ = cv2.connectedComponentsWithStats(sand.astype(np.uint8), 8)
    sand_regions = np.zeros(sand_count, dtype=np.uint8)
    sand_regions[1:] = sand_stats[1:, cv2.CC_STAT_AREA] > 5000
    sand_nearby = cv2.dilate(sand_regions[sand_labels], np.ones((11, 11), np.uint8)) != 0
    y, x = np.ogrid[:height, :width]
    beach_zone = ((x > 3500) & (x < 4090) & (y < 802)) | ((x > 4750) & (y < 882))
    beach_edge = water & (edge_distance < 2.5) & sand_nearby & beach_zone
    beach_distance = cv2.distanceTransform((~beach_edge).astype(np.uint8), cv2.DIST_L2, 5)

    # Project solid silhouettes into the water. This retains pier contact and
    # reflections without extracting the painted ripples from the reference.
    solid = (~water).astype(np.float32)
    pier_shadow = np.zeros_like(solid)
    for shift_x, shift_y, weight in [(0, 6, 0.30), (4, 16, 0.30), (7, 30, 0.25), (10, 46, 0.15)]:
        shifted = cv2.warpAffine(
            solid, np.float32([[1, 0, shift_x], [0, 1, shift_y]]), (width, height),
            flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE,
        )
        pier_shadow += shifted * weight
    quay_shadow = np.zeros_like(solid)
    for shift_y, weight in [(3, 0.30), (6, 0.30), (10, 0.25), (17, 0.15)]:
        shifted = cv2.warpAffine(
            solid, np.float32([[1, 0, 0], [0, 1, shift_y]]), (width, height),
            flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE,
        )
        quay_shadow += shifted * weight
    wooden_piers = ((x > 3140) & (x < 4096) & (y > 740)) | ((x > 5390) & (x < 5900) & (y > 790))
    shadow = np.where(wooden_piers, pier_shadow, quay_shadow)
    shadow = cv2.GaussianBlur(shadow, (9, 3), 0) * water
    # Sand gets pale shallows, while stone walls and piers cast dark reflections.
    shadow *= np.clip(beach_distance / 32.0, 0.0, 1.0)

    layout = np.stack([
        coverage * 255,
        np.rint(np.clip(edge_distance / 128.0, 0.0, 1.0) * 255).astype(np.uint8),
        np.rint(np.clip(beach_distance / 192.0, 0.0, 1.0) * 255).astype(np.uint8),
        np.rint(np.clip(shadow, 0.0, 1.0) * 255).astype(np.uint8),
    ], axis=-1)
    Image.fromarray(layout).save(OUTPUT)
    print(f"Saved {OUTPUT.relative_to(ROOT)}: {width} x {height}, water {water.mean():.2%}")


if __name__ == "__main__":
    build_layout()
