"""Build local 2D board layers; originals are never modified.

The supplied image remains untouched; separate alpha patches clean its static
hand and correct the stock grid behind live cards and price markers. No external service.
"""
from pathlib import Path
import argparse
from PIL import Image
import shutil

ROOT = Path(__file__).resolve().parents[2]
ART = Path(__file__).resolve().parent / "art"


def build_fan_patch(image: Image.Image) -> Image.Image:
    """Remove only the baked-in hand; keep the original PNG and all other pixels.

    The mask follows the reference fan's upper edge and runs off the bottom.
    Local inpainting supplies scenery behind 0/1-card hands, not a new HUD panel.
    """
    import cv2
    import numpy as np
    from PIL import ImageDraw

    mask = Image.new("L", image.size)
    ImageDraw.Draw(mask).polygon([
        (396, 974), (430, 950), (501, 926), (562, 910), (620, 899),
        (745, 899), (832, 907), (900, 917), (972, 931), (1033, 950),
        (1080, 960), (1080, 1086), (396, 1086),
    ], fill=255)
    repaired = cv2.inpaint(np.array(image.convert("RGB")), np.array(mask), 5, cv2.INPAINT_TELEA)
    patch = Image.fromarray(repaired).convert("RGBA")
    patch.putalpha(mask)
    return patch


def build_shares_layers(image: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Equalize the four reference-colored lanes without changing sign or frame.

    Reuse one clean reference cell's texture and divider widths for every color.
    The six bands keep their original heights and slight perspective offset.
    """
    from PIL import ImageDraw
    import numpy as np

    source = image.convert("RGB")
    mask = Image.new("L", image.size)
    pen = ImageDraw.Draw(mask)
    for box in [(1039, 689, 1085, 728), (1089, 689, 1141, 730),
                (1157, 711, 1203, 755), (1041, 765, 1090, 809),
                (1148, 796, 1190, 838), (1168, 817, 1214, 862)]:
        pen.ellipse(box, fill=255)
    repaired = source.copy()
    # Remove the two old disc tips above the colored grid, below the title.
    for y in range(689, 701):
        for x in range(1037, 1142):
            if mask.getpixel((x, y)):
                repaired.putpixel((x, y), source.getpixel((1144 + (x % 43), y)))
    # The full grid below is intentionally corrected, not preserved pixel-for-pixel.
    pen.rectangle((0, 701, image.width, image.height), fill=0)
    bands = [(701, 730), (730, 760), (760, 785),
             (785, 814), (814, 841), (841, 863)]
    lefts = [1037, 1039, 1041, 1043, 1045, 1048]
    old_rights = [1200, 1203, 1205, 1208, 1210, 1213]
    column_width = 41
    colors = [(205, 48, 53), (47, 127, 220), (247, 175, 25), (44, 186, 62)]
    # This red cell is unobstructed. All four columns share its exact geometry,
    # wood separators and texture; recoloring cannot let green intrude on yellow.
    donor = source.crop((1039, 730, 1090, 760))
    for row, (top, bottom) in enumerate(bands):
        cell = donor.resize((column_width, bottom - top), Image.Resampling.NEAREST)
        cell_pixels = np.array(cell)
        for column, color in enumerate(colors):
            colored = cell_pixels.copy()
            # Identical inset on all cells, with reference texture inside it.
            for y in range(3, bottom - top - 3):
                for x in range(3, column_width - 2):
                    sx = 1044 + int((x - 3) * 37 / (column_width - 5))
                    sy = 735 + int((y - 3) * 18 / (bottom - top - 6))
                    shade = source.getpixel((sx, sy))[0] / 205.0
                    colored[y, x] = np.clip(np.array(color) * shade, 0, 255)
            # Recolor red edge texels too; retain the original brown dividers.
            red = ((colored[:, :, 0].astype(float) > colored[:, :, 1] * 1.8)
                   & (colored[:, :, 0].astype(float) > colored[:, :, 2] * 1.6)
                   & (colored[:, :, 0] > 150))
            red[3:bottom - top - 3, 3:column_width - 2] = False
            colored[red] = np.clip(cell_pixels[red, 0:1] / 205.0 * np.array(color), 0, 255)
            x = lefts[row] + column * column_width
            repaired.paste(Image.fromarray(colored), (x, top))
        right = lefts[row] + 4 * column_width
        # Clear a possible one-pixel remnant of the original oversized green lane.
        for x in range(right, old_rights[row]):
            repaired.paste(repaired.crop((right - 1, top, right, bottom)), (x, top))
        pen.rectangle((lefts[row], top, max(right, old_rights[row]) - 1, bottom - 1), fill=255)
    patch = repaired.convert("RGBA")
    patch.putalpha(mask)
    patch = patch.crop((1008, 646, 1240, 890))

    # The original dark disc supplies the stepped outline and face/shadow texture.
    # Tint copies with the reference's red, blue, yellow and green cell colors.
    tile = source.crop((1044, 766, 1087, 807))
    shape = Image.new("L", tile.size)
    ImageDraw.Draw(shape).polygon([(16, 1), (27, 1), (34, 6), (39, 14),
        (40, 25), (35, 34), (28, 39), (15, 39), (7, 33), (3, 24),
        (3, 14), (8, 6)], fill=255)
    luminance = np.asarray(tile).astype(float).mean(axis=2)
    atlas = Image.new("RGBA", (tile.width * 4, tile.height))
    for index, color in enumerate([(205, 48, 53), (47, 127, 220),
                                   (247, 175, 25), (44, 186, 62)]):
        intensity = np.clip(luminance / 65.0, 0.16, 1.35)
        rgb = np.clip(intensity[:, :, None] * color, 0, 255).astype("uint8")
        disc = Image.fromarray(rgb).convert("RGBA")
        disc.putalpha(shape)
        atlas.paste(disc, (index * tile.width, 0))
    return patch, atlas


def build(reference: Path) -> None:
    ART.mkdir(parents=True, exist_ok=True)
    original = ART / "reference.png"
    with Image.open(reference) as source:
        image = source.convert("RGB")
    if original.exists():
        with Image.open(original) as source:
            preserved = source.convert("RGB")
        if image.size != preserved.size or image.tobytes() != preserved.tobytes():
            raise ValueError("Reference differs from preserved original; it will not be overwritten")
    elif reference.resolve() != original.resolve():
        shutil.copyfile(reference, original)
    # No resizing, retouching, water fill or duplicated route: keep every pixel.
    image.save(ART / "harbor_board.png")
    build_fan_patch(image).save(ART / "fan_patch.png")
    shares_patch, shares_discs = build_shares_layers(image)
    shares_patch.save(ART / "shares_patch.png")
    shares_discs.save(ART / "shares_discs.png")
    for cargo in ["ginseng", "nutmeg", "silk", "jade"]:
        sprite = Image.open(ROOT / "ui" / "icons" / "hud" / f"{cargo}.png").convert("RGBA")
        sprite.thumbnail((88, 88), Image.Resampling.LANCZOS)
        sprite.save(ART / f"{cargo}.png")
    portrait = Image.open(ROOT / "card" / "image" / "lanka_avatar.png").convert("RGBA")
    portrait = portrait.crop((100, 70, 1030, 1000)).resize((112, 112), Image.Resampling.NEAREST)
    portrait.save(ART / "captain.png")
    print(f"Built native 2D board and five sprites in {ART}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    build(parser.parse_args().reference)
