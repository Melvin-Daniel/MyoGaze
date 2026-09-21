"""Fit the generated MyoGaze splash into Android density buckets."""

from pathlib import Path

from PIL import Image

SRC = Path(r"C:\Users\MELVIN\.cursor\projects\c-Users-MELVIN-Projects-NeuroShift\assets\myogaze-splash.png")
ROOT = Path(__file__).resolve().parents[1]
BG = (244, 246, 249)

SIZES = {
    "drawable/splash.png": (480, 800),
    "drawable-port-mdpi/splash.png": (320, 480),
    "drawable-port-hdpi/splash.png": (480, 800),
    "drawable-port-xhdpi/splash.png": (720, 1280),
    "drawable-port-xxhdpi/splash.png": (1080, 1920),
    "drawable-port-xxxhdpi/splash.png": (1440, 2560),
    "drawable-land-mdpi/splash.png": (480, 320),
    "drawable-land-hdpi/splash.png": (800, 480),
    "drawable-land-xhdpi/splash.png": (1280, 720),
    "drawable-land-xxhdpi/splash.png": (1920, 1080),
    "drawable-land-xxxhdpi/splash.png": (2560, 1440),
}


def cover(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    nw, nh = int(im.width * scale), int(im.height * scale)
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def contain(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGB", size, BG)
    tw, th = size
    scale = min(tw / im.width, th / im.height)
    nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
    return canvas


def main() -> None:
    src = Image.open(SRC).convert("RGB")
    public = ROOT / "web" / "public"
    public.mkdir(parents=True, exist_ok=True)
    src.save(public / "splash.png", "PNG", optimize=True)

    res = ROOT / "web" / "android" / "app" / "src" / "main" / "res"
    for rel, size in SIZES.items():
        out = res / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        img = contain(src, size) if size[0] > size[1] else cover(src, size)
        img.save(out, "PNG", optimize=True)
        print(f"{rel} {img.size}")


if __name__ == "__main__":
    main()
