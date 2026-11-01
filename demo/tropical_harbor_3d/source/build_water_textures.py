"""Build small seamless scalar textures; no external images or network required."""
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(23041)
size = 512

def field(power, cutoff):
    white = rng.normal(size=(size, size))
    spectrum = np.fft.rfft2(white)
    fy = np.fft.fftfreq(size)[:, None] * size
    fx = np.fft.rfftfreq(size)[None, :] * size
    radius = np.sqrt(fx * fx + fy * fy)
    filt = np.maximum(radius, 1.0) ** (-power)
    filt *= np.exp(-(radius / cutoff) ** 4)
    filt[0, 0] = 0
    out = np.fft.irfft2(spectrum * filt, s=(size, size))
    out = (out - out.mean()) / out.std()
    return np.clip(out * 0.165 + 0.5, 0, 1)

out = ROOT / 'assets'
out.mkdir(parents=True, exist_ok=True)
channels = [field(1.1, 85), field(1.35, 55), field(0.8, 110)]
Image.fromarray((np.stack(channels, axis=-1) * 255).astype('uint8'), 'RGB').save(out / 'water_noise.png')
print('TEXTURE_OK', out / 'water_noise.png')
