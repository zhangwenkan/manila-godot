"""Prepare transparent HUD textures from the user's replacement cargo artwork.

Run `python tools/build_hud_cargo.py` after replacing images in ui/icons/.
Clean, tightly cropped copies go to ui/icons/hud/; source images are untouched.
"""

import argparse
from pathlib import Path

from PIL import Image, ImageChops


ASSET_NAMES = ("backdrop", "silk", "nutmeg", "jade", "ginseng")
ICON_DIRECTORY = Path(__file__).resolve().parents[1] / "ui" / "icons"


def prepare_texture(source: Path) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    # The cutouts contain faint gray alpha residue well outside the pixel art.
    alpha = image.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    if source.stem == "backdrop":
        # The board's clipped corners still contain opaque checkerboard pixels.
        red, green, blue = image.convert("RGB").split()
        lightest = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        darkest = ImageChops.darker(ImageChops.darker(red, green), blue)
        neutral = ImageChops.subtract(lightest, darkest).point(
            lambda value: 255 if value < 20 else 0
        )
        light = darkest.point(lambda value: 255 if value >= 160 else 0)
        alpha = ImageChops.subtract(alpha, ImageChops.multiply(neutral, light))
    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError(f"No visible artwork in {source}")
    image.putalpha(alpha)
    cropped = image.crop(bounds)
    # Transparent pixels carry no white/gray color into the imported texture.
    clean = Image.new("RGBA", cropped.size)
    clean.paste(cropped, mask=cropped.getchannel("A"))
    return clean


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ICON_DIRECTORY)
    parser.add_argument("--output-dir", type=Path, default=ICON_DIRECTORY / "hud")
    args = parser.parse_args()
    if args.source_dir.resolve() == args.output_dir.resolve():
        parser.error("The output directory must be separate from the originals")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name in ASSET_NAMES:
        texture = prepare_texture(args.source_dir / f"{name}.png")
        destination = args.output_dir / f"{name}.png"
        texture.save(destination)
        print(f"Saved {destination.name}: {texture.width} x {texture.height}")


if __name__ == "__main__":
    main()
