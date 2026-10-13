"""
Generate clean, branded placeholder screenshots for the README / landing page.

These are NOT fake UI captures pretending to be the real app — they are
clearly-labelled preview graphics rendered from the project's own logo and
theme palette, so the README always looks professional even before real
captures are taken. Replace them with real screenshots any time:

    Run the app, take a screenshot, save over the matching file in
    docs/screenshots/ (keep the same filenames).

Usage:
    python docs/generate_screenshots.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "icons"
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

LOGO = ICONS / "icon256.png"
FONT_BOLD = ICONS / "Inter-Bold.ttf"
FONT_LIGHT = ICONS / "Inter-Light.ttf"

# DLite palette
BG = (16, 20, 28)
PANEL = (24, 30, 42)
PANEL_2 = (30, 38, 54)
BRAND = (76, 175, 80)
BRAND_DARK = (44, 122, 48)
TEXT = (240, 242, 245)
MUTED = (140, 150, 165)
LINE = (44, 54, 72)


def font(path, size):
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def rounded_rect(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def header(img, draw, title, w):
    f = font(FONT_BOLD, 30)
    draw.text((40, 28), title, fill=TEXT, font=f)
    f2 = font(FONT_LIGHT, 14)
    draw.text((40, 66), "DLite — Fast, Free & Open-Source Download Manager", fill=MUTED, font=f2)
    # accent
    draw.rectangle((40, 96, 120, 100), fill=BRAND)


def sidebar(draw, items, active=0):
    x0, y0, w_item, h_item = 28, 120, 190, 44
    f = font(FONT_BOLD, 15)
    for i, name in enumerate(items):
        y = y0 + i * (h_item + 6)
        if i == active:
            rounded_rect(draw, (x0, y, x0 + w_item, y + h_item), 8, BRAND_DARK)
        else:
            rounded_rect(draw, (x0, y, x0 + w_item, y + h_item), 8, PANEL_2)
        draw.text((x0 + 16, y + 11), name, fill=TEXT if i == active else MUTED, font=f)


def main_window():
    w, h = 1280, 800
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    header(img, draw, "Downloads", w)
    sidebar(draw, ["All", "Video", "Audio", "Documents", "Archives", "Images", "Programs"], active=0)

    # Toolbar
    tb_y = 120
    for i, label in enumerate(["Add URL", "Resume", "Pause", "Cancel", "Remove"]):
        x = 240 + i * 120
        rounded_rect(draw, (x, tb_y, x + 108, tb_y + 36), 8, PANEL_2)
        draw.text((x + 14, tb_y + 9), label, fill=TEXT, font=font(FONT_BOLD, 12))

    # Table header
    cols = ["File", "Size", "Status", "Speed", "Progress"]
    xs = [240, 600, 740, 880, 1020]
    for c, x in zip(cols, xs, strict=True):
        draw.text((x, 184), c, fill=MUTED, font=font(FONT_BOLD, 12))
    draw.line((240, 206, w - 28, 206), fill=LINE, width=1)

    rows = [
        ("ubuntu-24.04.iso", "3.2 GB", "Downloading", "12.4 MB/s", 0.62),
        ("dataset.zip", "880 MB", "Queued", "—", 0.0),
        ("lecture-video.mp4", "540 MB", "Completed", "—", 1.0),
        ("report.pdf", "2.1 MB", "Completed", "—", 1.0),
        ("backup.tar.gz", "1.4 GB", "Paused", "—", 0.31),
    ]
    for i, (name, size, status, speed, prog) in enumerate(rows):
        y = 222 + i * 56
        if i % 2 == 0:
            draw.rectangle((240, y, w - 28, y + 50), fill=PANEL)
        draw.text((xs[0], y + 16), name, fill=TEXT, font=font(FONT_BOLD, 13))
        draw.text((xs[1], y + 16), size, fill=MUTED, font=font(FONT_LIGHT, 12))
        col = BRAND if status == "Completed" else (MUTED if status != "Downloading" else (66, 165, 245))
        draw.text((xs[2], y + 16), status, fill=col, font=font(FONT_BOLD, 12))
        draw.text((xs[3], y + 16), speed, fill=TEXT, font=font(FONT_LIGHT, 12))
        # progress bar
        bx0, by0, bx1, by1 = xs[4], y + 18, w - 48, y + 30
        rounded_rect(draw, (bx0, by0, bx1, by1), 6, PANEL_2)
        fw = int((bx1 - bx0) * prog)
        if fw > 0:
            rounded_rect(draw, (bx0, by0, bx0 + fw, by1), 6, BRAND)

    # Speed graph mini
    gx, gy, gw, gh = 240, 520, w - 268, 200
    rounded_rect(draw, (gx, gy, gx + gw, gy + gh), 10, PANEL)
    draw.text((gx + 16, gy + 14), "Speed (60s)", fill=MUTED, font=font(FONT_BOLD, 13))
    import math
    pts = [(gx + 20 + j * (gw - 40) / 60, gy + gh - 30 - (math.sin(j / 4) * 40 + math.sin(j / 9) * 30 + 70))
           for j in range(61)]
    draw.line(pts, fill=BRAND, width=2)
    for p in pts:
        draw.ellipse((p[0] - 1, p[1] - 1, p[0] + 1, p[1] + 1), fill=BRAND)

    # status bar
    draw.rectangle((0, h - 30, w, h), fill=PANEL_2)
    draw.text((240, h - 22), "3 active  •  2 queued  •  Total: 12.4 MB/s", fill=MUTED, font=font(FONT_LIGHT, 12))

    img.save(OUT / "main-window.png")
    print("saved main-window.png")


def add_download():
    w, h = 720, 520
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    rounded_rect(draw, (40, 40, w - 40, h - 40), 14, PANEL)
    draw.text((70, 70), "Add New Download", fill=TEXT, font=font(FONT_BOLD, 22))
    draw.rectangle((70, 108, 150, 112), fill=BRAND)

    fields = [
        ("URL", "https://releases.ubuntu.com/24.04/ubuntu-24.04.3-desktop-amd64.iso"),
        ("Filename", "ubuntu-24.04.3-desktop-amd64.iso"),
        ("Save to", "C:\\Users\\safou\\Downloads\\DLite"),
        ("Category", "Programs"),
        ("Segments", "8"),
        ("Speed limit", "0 KB/s  (unlimited)"),
    ]
    y = 134
    for label, value in fields:
        draw.text((70, y), label, fill=MUTED, font=font(FONT_BOLD, 13))
        rounded_rect(draw, (70, y + 22, w - 70, y + 58), 8, PANEL_2)
        draw.text((86, y + 30), value, fill=TEXT, font=font(FONT_LIGHT, 14))
        y += 78

    # buttons
    rounded_rect(draw, (w - 250, h - 100, w - 130, h - 56), 8, PANEL_2)
    draw.text((w - 220, h - 90), "Cancel", fill=MUTED, font=font(FONT_BOLD, 14))
    rounded_rect(draw, (w - 122, h - 100, w - 62, h - 56), 8, BRAND)
    draw.text((w - 110, h - 90), "Start", fill=(255, 255, 255), font=font(FONT_BOLD, 14))
    img.save(OUT / "add-download.png")
    print("saved add-download.png")


def settings():
    w, h = 860, 620
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    rounded_rect(draw, (40, 40, w - 40, h - 40), 14, PANEL)
    draw.text((70, 70), "Settings", fill=TEXT, font=font(FONT_BOLD, 22))
    draw.rectangle((70, 108, 150, 112), fill=BRAND)

    tabs = ["General", "Connection", "Browser Extensions", "Theme"]
    tx = 70
    for i, t in enumerate(tabs):
        fw = len(t) * 8 + 24
        fill = PANEL_2 if i != 2 else BRAND_DARK
        rounded_rect(draw, (tx, 130, tx + fw, 168), 8, fill)
        col = TEXT if i == 2 else MUTED
        draw.text((tx + 12, 140), t, fill=col, font=font(FONT_BOLD, 13))
        tx += fw + 8

    rows = [
        "Detected browsers:  Chrome, Edge, Firefox",
        "Native host status:  Registered ✓",
        "Listen port:  38271",
        "Intercept downloads automatically:  ON",
        "Right-click context menu:  ON",
    ]
    y = 196
    for r in rows:
        draw.text((80, y), r, fill=TEXT, font=font(FONT_LIGHT, 15))
        y += 44

    rounded_rect(draw, (80, y + 4, 280, y + 46), 8, BRAND)
    draw.text((104, y + 14), "Register Native Host", fill=(255, 255, 255), font=font(FONT_BOLD, 14))

    img.save(OUT / "settings.png")
    print("saved settings.png")


def browser_extension():
    w, h = 420, 320
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    rounded_rect(draw, (20, 20, w - 20, h - 20), 12, PANEL)
    # logo
    try:
        logo = Image.open(LOGO).convert("RGBA").resize((56, 56))
        img.paste(logo, (40, 44), logo)
    except OSError:
        pass
    draw.text((110, 52), "DLite", fill=TEXT, font=font(FONT_BOLD, 20))
    draw.text((110, 78), "Connected to desktop", fill=BRAND, font=font(FONT_LIGHT, 12))

    draw.line((40, 116, w - 40, 116), fill=LINE, width=1)
    draw.text((40, 132), "Status", fill=MUTED, font=font(FONT_BOLD, 11))
    draw.text((40, 152), "Listening on port 38271", fill=TEXT, font=font(FONT_LIGHT, 13))

    draw.text((40, 190), "Auto-capture downloads", fill=MUTED, font=font(FONT_BOLD, 11))
    # toggle on
    rounded_rect(draw, (w - 80, 188, w - 40, 212), 12, BRAND)
    draw.ellipse((w - 56, 190, w - 40, 206), fill=(255, 255, 255))

    rounded_rect(draw, (40, 240, w - 40, 284), 8, BRAND_DARK)
    draw.text((104, 252), "Open DLite", fill=(255, 255, 255), font=font(FONT_BOLD, 14))
    img.save(OUT / "browser-extension.png")
    print("saved browser-extension.png")


if __name__ == "__main__":
    main_window()
    add_download()
    settings()
    browser_extension()
    print("\nDone. Screenshots written to", OUT)