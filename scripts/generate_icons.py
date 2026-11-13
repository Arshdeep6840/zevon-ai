"""Generate all Zevon icons from one drawing (requires Pillow). Run from the project root:
    python scripts/generate_icons.py
Then (desktop):  cd frontend && npx tauri icon src-tauri/app-icon.png
Edit BG/FG colors or draw() to rebrand."""
from pathlib import Path

from PIL import Image, ImageDraw

BG, FG = (15, 23, 42), (56, 189, 248)
ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "frontend"
RES = FRONT / "android" / "app" / "src" / "main" / "res"
S = 2048  # draw large, downscale for smooth edges


def art(size: int, scale: float, bg: bool, rounded: bool = True, circle: bool = False) -> Image.Image:
    """Ring + dot mark. scale = fraction of the canvas the mark may use (adaptive icons need ~0.6)."""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if bg:
        if circle:
            d.ellipse((0, 0, S - 1, S - 1), fill=BG)
        elif rounded:
            d.rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.22), fill=BG)
        else:
            d.rectangle((0, 0, S, S), fill=BG)
    c, r = S / 2, S * scale / 2
    d.ellipse((c - r, c - r, c + r, c + r), outline=FG, width=int(S * scale * 0.12))
    dot = r * 0.34
    d.ellipse((c - dot, c - dot, c + dot, c + dot), fill=FG)
    return img.resize((size, size), Image.LANCZOS)


def save(img, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def main():
    save(art(1024, 0.52, True), FRONT / "src-tauri" / "app-icon.png")          # source for `tauri icon`
    pub = FRONT / "public"
    save(art(192, 0.52, True), pub / "icon-192.png")
    save(art(512, 0.52, True), pub / "icon-512.png")
    save(art(512, 0.40, True, rounded=False), pub / "icon-maskable-512.png")     # full-bleed, mark inside safe zone
    for name, px, fg in [("mdpi", 48, 108), ("hdpi", 72, 162), ("xhdpi", 96, 216), ("xxhdpi", 144, 324), ("xxxhdpi", 192, 432)]:
        d = RES / f"mipmap-{name}"
        save(art(px, 0.52, True), d / "ic_launcher.png")
        save(art(px, 0.52, True, circle=True), d / "ic_launcher_round.png")
        save(art(fg, 0.40, False), d / "ic_launcher_foreground.png")             # adaptive: transparent, mark in safe zone
    bgxml = RES / "values" / "ic_launcher_background.xml"
    bgxml.write_text('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#0F172A</color>\n</resources>\n')
    print("icons generated")


if __name__ == "__main__":
    main()
