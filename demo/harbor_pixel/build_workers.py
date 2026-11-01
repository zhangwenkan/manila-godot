"""Keep the supplied worker scene intact and fit a copy to the demo's coordinates."""
from pathlib import Path
import hashlib
import sys

from PIL import Image

ART = Path(__file__).parent / "art"
SOURCE = ART / "harbor_workers_reference.png"
BOARD = ART / "harbor_workers_board.png"
SOURCE_SHA256 = "6ffb9719ef5a946c815606846579f9a8640d0400acd6a477f0b7617d91ecd17b"


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE
    content = source.read_bytes()
    if hashlib.sha256(content).hexdigest() != SOURCE_SHA256:
        raise ValueError("Input differs from the supplied three-worker scene")
    if SOURCE.exists() and SOURCE.read_bytes() != content:
        raise ValueError("Refusing to replace the preserved worker reference")
    if not SOURCE.exists():
        SOURCE.write_bytes(content)
    with Image.open(SOURCE) as image:
        if image.size != (1456, 1088):
            raise ValueError("Expected the original 1456x1088 worker scene")
        # The overall scene registration matches this full-frame size mapping.
        image.convert("RGB").resize((1448, 1086), Image.Resampling.NEAREST).save(BOARD)
    print(f"Built {BOARD.name}; both original scene references remain untouched")


if __name__ == "__main__":
    main()
