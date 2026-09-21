"""Render the MyoGaze mark: open gaze-C + EMG spike.

Insider meaning (viva):
  Open C     = gaze / dwell. Looking never closes the act on its own.
  EMG spike  = muscle confirm. The only signal allowed to occupy the gap.
  Empty core = abstain-by-default; nothing is on until both channels agree.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BLUE = (11, 92, 213, 255)
WHITE = (255, 255, 255, 255)

# Design space is 24×24. 0° = 3 o'clock, y increases downward.
CX, CY = 12.0, 12.0
RING_R = 7.05
GAP = 50.0


def polar(deg: float, rad: float) -> tuple[float, float]:
    a = math.radians(deg)
    return (CX + rad * math.cos(a), CY + rad * math.sin(a))


def _xform(x: float, y: float, scale: float, ox: float, oy: float) -> tuple[float, float]:
    return (x * scale + ox, y * scale + oy)


def ring_path(scale: float = 1.0, ox: float = 0.0, oy: float = 0.0) -> str:
    start = polar(GAP, RING_R)
    end = polar(-GAP, RING_R)
    r = RING_R * scale
    sx, sy = _xform(*start, scale, ox, oy)
    ex, ey = _xform(*end, scale, ox, oy)
    return f"M{sx:.2f},{sy:.2f} A{r:.2f},{r:.2f} 0 1 1 {ex:.2f},{ey:.2f}"


def spike_centerline() -> list[tuple[float, float]]:
    """Vertical QRS pulse in the C's opening (read top → bottom, R-wave to the right)."""
    x0 = CX + RING_R - 0.15
    return [
        (x0, CY - 3.9),
        (x0, CY - 2.35),
        (x0 - 1.85, CY - 1.25),
        (x0 + 3.55, CY),
        (x0 - 1.85, CY + 1.25),
        (x0, CY + 2.35),
        (x0, CY + 3.9),
    ]


def spike_path(scale: float = 1.0, ox: float = 0.0, oy: float = 0.0) -> str:
    cmds: list[str] = []
    for i, (x, y) in enumerate(spike_centerline()):
        px, py = _xform(x, y, scale, ox, oy)
        cmds.append(f"{'M' if i == 0 else 'L'}{px:.2f},{py:.2f}")
    return " ".join(cmds)


def draw_mark(
    size: int,
    *,
    color: tuple[int, int, int, int],
    pad_ratio: float = 0.0,
) -> Image.Image:
    inner = int(size * (1.0 - pad_ratio))
    hi = max(inner * 4, 256)
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    scale = hi / 24.0
    stroke = max(3, int(2.35 * scale))

    bbox = [
        CX * scale - RING_R * scale,
        CY * scale - RING_R * scale,
        CX * scale + RING_R * scale,
        CY * scale + RING_R * scale,
    ]
    draw.arc(bbox, start=GAP, end=360 - GAP, fill=color, width=stroke)
    cap = stroke / 2
    for deg in (GAP, -GAP):
        px, py = polar(deg, RING_R)
        px, py = px * scale, py * scale
        draw.ellipse((px - cap, py - cap, px + cap, py + cap), fill=color)

    sp = [(x * scale, y * scale) for x, y in spike_centerline()]
    spike_w = max(3, int(1.9 * scale))
    draw.line(sp, fill=color, width=spike_w, joint="miter")
    rcap = spike_w / 2
    for x, y in (sp[0], sp[3], sp[-1]):
        draw.ellipse((x - rcap, y - rcap, x + rcap, y + rcap), fill=color)

    mark = img.resize((inner, inner), Image.Resampling.LANCZOS)
    if pad_ratio <= 0:
        return mark
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    off = (size - inner) // 2
    canvas.paste(mark, (off, off), mark)
    return canvas


def _squircle(size: int, radius: float) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return m


def make_launcher(size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), BLUE)
    canvas.putalpha(_squircle(size, size * 0.22))
    mark = draw_mark(size, color=WHITE, pad_ratio=0.04)
    canvas.alpha_composite(mark)
    return canvas


def svg_mark(*, filled_bg: bool, fg: str, bg: str | None = None) -> str:
    ring = ring_path()
    spike = spike_path()
    bg_el = f'  <rect width="24" height="24" rx="5.4" fill="{bg}"/>\n' if filled_bg and bg else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">\n'
        f"{bg_el}"
        f'  <path d="{ring}" stroke="{fg}" stroke-width="2.35" stroke-linecap="round"/>\n'
        f'  <path d="{spike}" stroke="{fg}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="miter" />\n'
        f"</svg>\n"
    )


def android_vector(*, color: str, viewport: int = 108) -> str:
    # Keep the mark inside the adaptive-icon / splash circular safe zone (~66%).
    inset = viewport * 0.18
    scale = (viewport - 2 * inset) / 24.0
    ox = oy = inset
    ring = ring_path(scale, ox, oy)
    spike = spike_path(scale, ox, oy)
    sw = 2.35 * scale
    return f"""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="{viewport}dp"
    android:height="{viewport}dp"
    android:viewportWidth="{viewport}"
    android:viewportHeight="{viewport}">
    <path
        android:pathData="{ring}"
        android:fillColor="#00000000"
        android:strokeColor="{color}"
        android:strokeWidth="{sw:.2f}"
        android:strokeLineCap="round"
        android:strokeLineJoin="round" />
    <path
        android:pathData="{spike}"
        android:fillColor="#00000000"
        android:strokeColor="{color}"
        android:strokeWidth="{sw * 1.9 / 2.35:.2f}"
        android:strokeLineCap="round"
        android:strokeLineJoin="miter"
        android:strokeMiterLimit="8" />
</vector>
"""


def main() -> None:
    out_pub = ROOT / "web" / "public"
    out_pub.mkdir(parents=True, exist_ok=True)
    make_launcher(1024).save(out_pub / "app-icon.png", "PNG")
    make_launcher(180).save(out_pub / "apple-touch-icon.png", "PNG")
    draw_mark(512, color=BLUE).save(out_pub / "splash-mark.png", "PNG")
    (out_pub / "favicon.svg").write_text(svg_mark(filled_bg=True, fg="#FFFFFF", bg="#0B5CD5"), encoding="utf-8")
    (out_pub / "mark.svg").write_text(svg_mark(filled_bg=False, fg="#0B5CD5"), encoding="utf-8")

    res = ROOT / "web" / "android" / "app" / "src" / "main" / "res"
    densities = {
        "mdpi": 108,
        "hdpi": 162,
        "xhdpi": 216,
        "xxhdpi": 324,
        "xxxhdpi": 432,
    }
    for name, px in densities.items():
        folder = res / f"mipmap-{name}"
        folder.mkdir(parents=True, exist_ok=True)
        draw_mark(px, color=WHITE, pad_ratio=0.10).save(folder / "ic_launcher_foreground.png", "PNG")
        icon = make_launcher(px)
        icon.save(folder / "ic_launcher.png", "PNG")
        icon.save(folder / "ic_launcher_round.png", "PNG")

    drawable = res / "drawable"
    drawable.mkdir(parents=True, exist_ok=True)
    (drawable / "splash_logo.xml").write_text(android_vector(color="#0B5CD5"), encoding="utf-8")
    (res / "drawable-v24").mkdir(parents=True, exist_ok=True)
    fg = android_vector(color="#FFFFFF")
    (res / "drawable-v24" / "ic_launcher_foreground.xml").write_text(fg, encoding="utf-8")
    (drawable / "ic_launcher_foreground.xml").write_text(fg, encoding="utf-8")
    (drawable / "ic_launcher_background.xml").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#0B5CD5"
        android:pathData="M0,0h108v108h-108z" />
</vector>
""",
        encoding="utf-8",
    )
    print("wrote launcher + splash mark")


if __name__ == "__main__":
    main()
