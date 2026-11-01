"""Crop the supplied stock icon; keep the original reference untouched."""
from pathlib import Path
from PIL import Image
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('reference', type=Path)
args = parser.parse_args()
image = Image.open(args.reference).convert('RGBA')
alpha = image.getchannel('A')
mask = alpha.point(lambda v: 255 if v >= 64 else 0)
bounds = mask.getbbox()
if bounds is None:
    raise ValueError('Reference has no opaque icon')
image.putalpha(alpha.point(lambda v: v if v >= 64 else 0))
image = image.crop(bounds)
image.thumbnail((64, 64), Image.Resampling.NEAREST)
out = Path(__file__).resolve().parent / 'art' / 'market_icon.png'
if out.exists():
    raise FileExistsError('Inspect existing icon before replacing it')
image.save(out)
print('MARKET_ICON', bounds, image.size, out)
