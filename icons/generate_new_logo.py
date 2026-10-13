#!/usr/bin/env python3
"""
DLite — Official Brand & Asset Generator
=========================================
100% original, procedurally synthesized brand identity:
  • Aerodynamic Turbo-Speed Chevrons (Electric Cyan -> Emerald Mint)
  • Multi-stream segmented acceleration indicators
  • Sleek dark-glass squircle badge with ambient glow

Generates:
  • Multi-resolution PNG icons (16, 32, 48, 64, 128, 256, 512, 1024, 4K)
  • Windows ICO (multi-res: 16, 32, 48, 64, 128, 256)
  • macOS ICNS (multi-res: 16, 32, 64, 128, 256, 512, 1024)
  • Favicon ICO (16, 32)
  • Wordmark logos (logo_light_full.png, logo_dark_full.png)
  • GitHub Banner (1280x640)
  • GitHub Social Preview (1280x640)
  • Browser extension icons for Chromium and Firefox
"""

import math
import os
import shutil
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
WEBSITE_DIR = os.path.join(PROJECT_ROOT, "website")
CHROMIUM_ICONS = os.path.join(PROJECT_ROOT, "browser-extension", "chromium", "icons")
FIREFOX_ICONS = os.path.join(PROJECT_ROOT, "browser-extension", "firefox", "icons")

FONT_BOLD_PATH = os.path.join(BASE_DIR, "Inter-Bold.ttf")
FONT_LIGHT_PATH = os.path.join(BASE_DIR, "Inter-Light.ttf")

ICON_SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("arial.ttf", size)
        except (OSError, IOError):
            return ImageFont.load_default()


def _ensure_dirs():
    for d in [DOCS_DIR, WEBSITE_DIR, CHROMIUM_ICONS, FIREFOX_ICONS]:
        os.makedirs(d, exist_ok=True)


# ==============================================================================
# 1. Procedural Master Icon Generator (2048x2048 supersampled)
# ==============================================================================
def create_master_icon(size=2048):
    """
    Renders the DLite squircle badge with turbo chevrons and multi-stream pills
    at 2x resolution with LANCZOS downsampling for crisp, aliasing-free output.
    """
    S = size * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    s = S / 1024.0

    # ── 1. Outer Squircle Badge with Ambient Shadow ──
    m = int(72 * s)
    radius = int(216 * s)
    rect = [m, m, S - m, S - m]

    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    shadow_offset = int(32 * s)
    s_draw.rounded_rectangle(
        [m, m + shadow_offset, S - m, S - m + shadow_offset],
        radius=radius,
        fill=(0, 0, 0, 130),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=int(40 * s)))
    img = Image.alpha_composite(img, shadow)

    # ── 2. Squircle Body Gradient ──
    badge = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mask = Image.new("L", (S, S), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle(rect, radius=radius, fill=255)

    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(grad)
    for y in range(m, S - m):
        t = (y - m) / (S - 2 * m)
        r = int(14 + 10 * math.sin(t * math.pi) - 4 * t)
        g = int(18 + 14 * math.sin(t * math.pi) - 5 * t)
        b = int(28 + 24 * math.sin(t * math.pi) - 8 * t)
        g_draw.line([(m, y), (S - m, y)], fill=(r, g, b, 255))
    badge.paste(grad, (0, 0), mask)

    # Ambient internal glow (electric cyan top, emerald bottom)
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gl_draw = ImageDraw.Draw(glow)
    gl_draw.ellipse(
        [int(200 * s), int(100 * s), int(824 * s), int(480 * s)],
        fill=(0, 229, 255, 38),
    )
    gl_draw.ellipse(
        [int(250 * s), int(560 * s), int(774 * s), int(880 * s)],
        fill=(16, 185, 129, 35),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=int(110 * s)))
    badge = Image.alpha_composite(
        badge, Image.composite(glow, Image.new("RGBA", (S, S), (0, 0, 0, 0)), mask)
    )

    # Metallic borders
    b_draw = ImageDraw.Draw(badge)
    b_draw.rounded_rectangle(
        rect, radius=radius, outline=(56, 189, 248, 80), width=int(6 * s)
    )
    b_draw.rounded_rectangle(
        [m + int(6 * s), m + int(6 * s), S - m - int(6 * s), S - m - int(6 * s)],
        radius=radius - int(6 * s),
        outline=(255, 255, 255, 18),
        width=int(2 * s),
    )
    img = Image.alpha_composite(img, badge)

    # ── 3. Main Emblem: Dual Aerodynamic Turbo Chevrons ──
    cx = S // 2

    # Top chevron (Cyan -> Sky Blue)
    c1_w = int(250 * s)
    c1_h = int(120 * s)
    c1_thick = int(82 * s)
    c1_y = int(270 * s)
    poly1 = [
        (cx - c1_w, c1_y),
        (cx, c1_y + c1_h),
        (cx + c1_w, c1_y),
        (cx + c1_w, c1_y + c1_thick),
        (cx, c1_y + c1_h + c1_thick),
        (cx - c1_w, c1_y + c1_thick),
    ]

    # Lower chevron (Vivid Cyan -> Emerald Mint)
    c2_w = int(270 * s)
    c2_h = int(150 * s)
    c2_thick = int(95 * s)
    c2_y = int(430 * s)
    poly2 = [
        (cx - c2_w, c2_y),
        (cx, c2_y + c2_h),
        (cx + c2_w, c2_y),
        (cx + c2_w, c2_y + c2_thick),
        (cx, c2_y + c2_h + c2_thick),
        (cx - c2_w, c2_y + c2_thick),
    ]

    # Drop shadow under chevrons
    chev_shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cs_draw = ImageDraw.Draw(chev_shadow)
    off1 = int(24 * s)
    cs_draw.polygon([(px, py + off1) for px, py in poly1], fill=(0, 0, 0, 130))
    cs_draw.polygon([(px, py + off1) for px, py in poly2], fill=(0, 0, 0, 160))
    chev_shadow = chev_shadow.filter(ImageFilter.GaussianBlur(radius=int(26 * s)))
    img = Image.alpha_composite(img, chev_shadow)

    # Chevron 1 layer
    c1_mask = Image.new("L", (S, S), 0)
    c1m_draw = ImageDraw.Draw(c1_mask)
    c1m_draw.polygon(poly1, fill=255)
    c1_grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    c1g_draw = ImageDraw.Draw(c1_grad)
    for y in range(c1_y, c1_y + c1_h + c1_thick + 1):
        t = (y - c1_y) / (c1_h + c1_thick)
        r = int(0 + 14 * t)
        g = int(245 + (165 - 245) * t)
        b = int(255 + (233 - 255) * t)
        c1g_draw.line([(0, y), (S, y)], fill=(r, g, b, 255))
    c1_layer = Image.composite(
        c1_grad, Image.new("RGBA", (S, S), (0, 0, 0, 0)), c1_mask
    )
    c1l_draw = ImageDraw.Draw(c1_layer)
    c1l_draw.line(
        [(cx - c1_w, c1_y), (cx, c1_y + c1_h), (cx + c1_w, c1_y)],
        fill=(255, 255, 255, 160),
        width=int(4 * s),
    )
    img = Image.alpha_composite(img, c1_layer)

    # Chevron 2 layer
    c2_mask = Image.new("L", (S, S), 0)
    c2m_draw = ImageDraw.Draw(c2_mask)
    c2m_draw.polygon(poly2, fill=255)
    c2_grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    c2g_draw = ImageDraw.Draw(c2_grad)
    for y in range(c2_y, c2_y + c2_h + c2_thick + 1):
        t = (y - c2_y) / (c2_h + c2_thick)
        r = int(0 + 16 * t)
        g = int(225 + (215 - 225) * t)
        b = int(255 + (135 - 255) * t)
        c2g_draw.line([(0, y), (S, y)], fill=(r, g, b, 255))
    c2_layer = Image.composite(
        c2_grad, Image.new("RGBA", (S, S), (0, 0, 0, 0)), c2_mask
    )
    c2l_draw = ImageDraw.Draw(c2_layer)
    c2l_draw.line(
        [(cx - c2_w, c2_y), (cx, c2_y + c2_h), (cx + c2_w, c2_y)],
        fill=(255, 255, 255, 180),
        width=int(5 * s),
    )
    img = Image.alpha_composite(img, c2_layer)

    # ── 4. Multi-Stream Parallel Acceleration Indicator Pills ──
    bar_y = int(740 * s)
    bar_h = int(34 * s)
    seg_w = int(105 * s)
    seg_gap = int(24 * s)
    num_segs = 4
    total_w = num_segs * seg_w + (num_segs - 1) * seg_gap
    start_x = cx - total_w // 2

    seg_shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ss_draw = ImageDraw.Draw(seg_shadow)
    for i in range(num_segs):
        bx = start_x + i * (seg_w + seg_gap)
        ss_draw.rounded_rectangle(
            [bx, bar_y + int(10 * s), bx + seg_w, bar_y + bar_h + int(10 * s)],
            radius=bar_h // 2,
            fill=(0, 0, 0, 110),
        )
    seg_shadow = seg_shadow.filter(ImageFilter.GaussianBlur(radius=int(14 * s)))
    img = Image.alpha_composite(img, seg_shadow)

    seg_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sl_draw = ImageDraw.Draw(seg_layer)
    for i in range(num_segs):
        bx = start_x + i * (seg_w + seg_gap)
        t = i / (num_segs - 1)
        cr = int(0 + 16 * t)
        cg = int(220 + 20 * t)
        cb = int(255 - 120 * t)
        sl_draw.rounded_rectangle(
            [bx, bar_y, bx + seg_w, bar_y + bar_h],
            radius=bar_h // 2,
            fill=(cr, cg, cb, 255),
        )
        sl_draw.line(
            [
                (bx + int(10 * s), bar_y + int(4 * s)),
                (bx + seg_w - int(10 * s), bar_y + int(4 * s)),
            ],
            fill=(255, 255, 255, 170),
            width=int(3 * s),
        )
    img = Image.alpha_composite(img, seg_layer)

    # Downscale with high quality LANCZOS filter
    final_img = img.resize((size, size), Image.LANCZOS)
    return final_img


def resize_square(img, size, padding_pct=0.04):
    """Square bounding box with centered content."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = int(size * (1 - padding_pct * 2))
    if inner < 1:
        inner = size
    thumb = img.copy()
    thumb.thumbnail((inner, inner), Image.LANCZOS)
    x = (size - thumb.width) // 2
    y = (size - thumb.height) // 2
    canvas.paste(thumb, (x, y), thumb)
    return canvas


# ==============================================================================
# 2. Asset Generation Functions
# ==============================================================================
def generate_icon_pngs(master_icon):
    generated = {}
    for size in ICON_SIZES:
        icon = resize_square(master_icon, size, padding_pct=0.03)
        path = os.path.join(BASE_DIR, f"icon{size}.png")
        icon.save(path, "PNG", optimize=True)
        generated[size] = path
        print(f"  [OK] icon{size}.png")

    # Default icon.png (128px)
    shutil.copy2(generated[128], os.path.join(BASE_DIR, "icon.png"))
    print("  [OK] icon.png (128px)")

    # 4K master
    icon_4k = resize_square(master_icon, 4096, padding_pct=0.02)
    icon_4k.save(os.path.join(BASE_DIR, "icon_4k.png"), "PNG", optimize=True)
    print("  [OK] icon_4k.png (4096px)")
    return generated


def generate_ico(master_icon):
    ico_sizes = [16, 32, 48, 64, 128, 256]
    frames = [resize_square(master_icon, s, padding_pct=0.04) for s in ico_sizes]
    path = os.path.join(BASE_DIR, "icon.ico")
    frames[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=frames[1:],
    )
    print(f"  [OK] icon.ico ({len(ico_sizes)} sizes)")

    # Favicon (16, 32)
    fav_frames = [
        resize_square(master_icon, 16, padding_pct=0.0),
        resize_square(master_icon, 32, padding_pct=0.0),
    ]
    fav_path = os.path.join(BASE_DIR, "favicon.ico")
    fav_frames[0].save(
        fav_path,
        format="ICO",
        sizes=[(16, 16), (32, 32)],
        append_images=fav_frames[1:],
    )
    print("  [OK] favicon.ico")


def generate_icns(master_icon):
    path = os.path.join(BASE_DIR, "icon.icns")
    icns_sizes = [16, 32, 64, 128, 256, 512, 1024]
    frames = [resize_square(master_icon, s, padding_pct=0.04) for s in icns_sizes]
    try:
        frames[0].save(path, format="ICNS", append_images=frames[1:])
        print(f"  [OK] icon.icns ({len(icns_sizes)} sizes)")
    except Exception as e:
        print(f"  [WARN] Could not generate ICNS: {e}")


def generate_wordmark_logos(master_icon):
    """
    Generate horizontal wordmark logos:
    [Icon Badge]  DLite
    Light & Dark background versions.
    """
    badge_size = 180
    badge = master_icon.resize((badge_size, badge_size), Image.LANCZOS)

    width, height = 720, 220
    font_bold = _font(FONT_BOLD_PATH, 86)
    font_sub = _font(FONT_LIGHT_PATH, 20)

    # ── Dark Version ──
    dark = Image.new("RGBA", (width, height), (16, 20, 28, 255))
    dark.paste(badge, (36, (height - badge_size) // 2), badge)
    d_draw = ImageDraw.Draw(dark)

    text_x = 240
    # "D" in Electric Cyan, "Lite" in Pure White
    d_draw.text((text_x, 48), "D", fill=(0, 229, 255), font=font_bold)
    bbox_d = d_draw.textbbox((text_x, 48), "D", font=font_bold)
    d_draw.text((bbox_d[2] + 2, 48), "Lite", fill=(245, 248, 255), font=font_bold)

    # Subtitle
    d_draw.text(
        (text_x, 142),
        "TURBO DOWNLOAD ACCELERATOR",
        fill=(130, 148, 170),
        font=font_sub,
    )
    dark_path = os.path.join(BASE_DIR, "logo_dark_full.png")
    dark.save(dark_path, "PNG", optimize=True)
    print("  [OK] logo_dark_full.png")

    # ── Light Version (Transparent background) ──
    light = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    light.paste(badge, (36, (height - badge_size) // 2), badge)
    l_draw = ImageDraw.Draw(light)

    l_draw.text((text_x, 48), "D", fill=(2, 132, 199), font=font_bold)
    bbox_dl = l_draw.textbbox((text_x, 48), "D", font=font_bold)
    l_draw.text((bbox_dl[2] + 2, 48), "Lite", fill=(15, 23, 42), font=font_bold)

    l_draw.text(
        (text_x, 142),
        "TURBO DOWNLOAD ACCELERATOR",
        fill=(100, 116, 139),
        font=font_sub,
    )
    light_path = os.path.join(BASE_DIR, "logo_light_full.png")
    light.save(light_path, "PNG", optimize=True)
    print("  [OK] logo_light_full.png")


def generate_github_banner(master_icon):
    """Create 1280x640 GitHub banner with sleek DLite identity."""
    W, H = 1280, 640
    banner = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(banner)

    # Vertical gradient: space navy (#090d16 -> #141c2c)
    for y in range(H):
        t = y / (H - 1)
        r = int(9 + 11 * t)
        g = int(13 + 15 * t)
        b = int(22 + 22 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    # Grid lines overlay
    grid_color = (255, 255, 255, 6)
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill=grid_color, width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill=grid_color, width=1)

    # Ambient glows
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        [W // 2 - 280, 40, W // 2 + 280, 440], fill=(0, 229, 255, 25)
    )
    glow_draw.ellipse(
        [W // 2 - 200, 160, W // 2 + 200, 480], fill=(16, 185, 129, 20)
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=80))
    banner = Image.alpha_composite(banner, glow)
    draw = ImageDraw.Draw(banner)

    # Center Emblem
    emblem_size = 230
    emblem = master_icon.resize((emblem_size, emblem_size), Image.LANCZOS)
    ex = (W - emblem_size) // 2
    ey = 70
    banner.paste(emblem, (ex, ey), emblem)

    # Title: DLITE
    title_font = _font(FONT_BOLD_PATH, 74)
    title_text = "DLITE"
    t_bb = draw.textbbox((0, 0), title_text, font=title_font)
    tw = t_bb[2] - t_bb[0]
    tx = (W - tw) // 2
    ty = ey + emblem_size + 24
    draw.text((tx, ty), title_text, fill=(255, 255, 255), font=title_font)

    # Tagline
    tag_font = _font(FONT_LIGHT_PATH, 24)
    tagline = "Modern, Ultra-Fast, Open-Source Download Manager"
    tag_bb = draw.textbbox((0, 0), tagline, font=tag_font)
    tag_w = tag_bb[2] - tag_bb[0]
    tag_x = (W - tag_w) // 2
    tag_y = ty + 82
    draw.text((tag_x, tag_y), tagline, fill=(160, 178, 200), font=tag_font)

    # Feature pills
    pill_font = _font(FONT_LIGHT_PATH, 16)
    pills = [
        "Multi-Stream Engine",
        "Browser Integration",
        "Pause & Resume",
        "Zero Ads & Bloat",
        "Open Source",
    ]
    pill_y = H - 85
    pill_measurements = []
    total_pw = 0
    for p in pills:
        bb = draw.textbbox((0, 0), p, font=pill_font)
        pw = bb[2] - bb[0] + 30
        pill_measurements.append((p, pw, bb[3] - bb[1]))
        total_pw += pw

    gap = 16
    total_w = total_pw + gap * (len(pills) - 1)
    cx = (W - total_w) // 2
    for p_text, pw, ph in pill_measurements:
        draw.rounded_rectangle(
            [cx, pill_y, cx + pw, pill_y + ph + 16],
            radius=12,
            fill=(255, 255, 255, 14),
            outline=(56, 189, 248, 45),
        )
        draw.text(
            (cx + 15, pill_y + 8), p_text, fill=(210, 224, 238), font=pill_font
        )
        cx += pw + gap

    banner_path = os.path.join(DOCS_DIR, "github_banner.png")
    banner.save(banner_path, "PNG", optimize=True)
    print("  [OK] github_banner.png (1280x640)")
    return banner_path


def generate_social_preview(master_icon):
    """Create 1280x640 Open Graph social preview."""
    W, H = 1280, 640
    preview = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(preview)

    for y in range(H):
        t = y / (H - 1)
        r = int(12 + 10 * t)
        g = int(16 + 14 * t)
        b = int(26 + 20 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        [W // 2 - 300, 20, W // 2 + 300, 480], fill=(0, 229, 255, 30)
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=90))
    preview = Image.alpha_composite(preview, glow)
    draw = ImageDraw.Draw(preview)

    emblem_size = 250
    emblem = master_icon.resize((emblem_size, emblem_size), Image.LANCZOS)
    ex = (W - emblem_size) // 2
    ey = 65
    preview.paste(emblem, (ex, ey), emblem)

    title_font = _font(FONT_BOLD_PATH, 80)
    title = "DLITE"
    t_bb = draw.textbbox((0, 0), title, font=title_font)
    tw = t_bb[2] - t_bb[0]
    draw.text(
        ((W - tw) // 2, ey + emblem_size + 20),
        title,
        fill=(255, 255, 255),
        font=title_font,
    )

    sub_font = _font(FONT_LIGHT_PATH, 28)
    subtitle = "Fast, Free & Open-Source Download Manager"
    s_bb = draw.textbbox((0, 0), subtitle, font=sub_font)
    sw = s_bb[2] - s_bb[0]
    draw.text(
        ((W - sw) // 2, ey + emblem_size + 115),
        subtitle,
        fill=(170, 188, 208),
        font=sub_font,
    )

    path = os.path.join(DOCS_DIR, "github_social_preview.png")
    preview.save(path, "PNG", optimize=True)
    print("  [OK] github_social_preview.png (1280x640)")
    return path


def distribute_icons():
    """Distribute generated icons to extensions, website, and docs."""
    chromium_sizes = {16: "icon16.png", 48: "icon48.png", 128: "icon128.png"}
    for size, name in chromium_sizes.items():
        src = os.path.join(BASE_DIR, f"icon{size}.png")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(CHROMIUM_ICONS, name))
            if size == 128:
                shutil.copy2(src, os.path.join(CHROMIUM_ICONS, "icon.png"))
    print("  [OK] Chromium extension icons updated")

    firefox_sizes = {
        16: "icon16.png",
        48: "icon48.png",
        96: "icon96.png",
        128: "icon128.png",
    }
    for size, name in firefox_sizes.items():
        if size == 96:
            src_128 = os.path.join(BASE_DIR, "icon128.png")
            if os.path.exists(src_128):
                img = Image.open(src_128).convert("RGBA")
                img = img.resize((96, 96), Image.LANCZOS)
                img.save(os.path.join(FIREFOX_ICONS, name), "PNG", optimize=True)
        else:
            src = os.path.join(BASE_DIR, f"icon{size}.png")
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(FIREFOX_ICONS, name))
                if size == 128:
                    shutil.copy2(src, os.path.join(FIREFOX_ICONS, "icon.png"))
    print("  [OK] Firefox extension icons updated")

    if os.path.exists(WEBSITE_DIR):
        for name in [
            "favicon.ico",
            "logo_light_full.png",
            "logo_dark_full.png",
            "icon128.png",
            "icon256.png",
        ]:
            src = os.path.join(BASE_DIR, name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(WEBSITE_DIR, name))
        print("  [OK] Website assets updated")


def cleanup_legacy_files():
    """Remove legacy/conflicting files."""
    legacy_files = [
        os.path.join(BASE_DIR, "logo_source.png"),
        os.path.join(DOCS_DIR, "f2d792f0-3f4c-4077-9772-6fe1cf18b5de.png"),
        os.path.join(BASE_DIR, "new_dlite_preview.png"),
        os.path.join(BASE_DIR, "new_dlite_preview2.png"),
    ]
    for p in legacy_files:
        if os.path.exists(p):
            try:
                os.remove(p)
                print(f"  [OK] Removed legacy file: {os.path.basename(p)}")
            except OSError as e:
                print(f"  [WARN] Could not remove {p}: {e}")


def main():
    print("=" * 60)
    print("  DLITE — Official Brand & Asset Generator")
    print("=" * 60)
    _ensure_dirs()

    print("[1/7] Synthesizing 100% original master emblem (2048x2048)...")
    master = create_master_icon(2048)

    print("[2/7] Generating icon PNGs (16 to 4K)...")
    generate_icon_pngs(master)

    print("[3/7] Generating Windows ICO & Favicon...")
    generate_ico(master)

    print("[4/7] Generating macOS ICNS...")
    generate_icns(master)

    print("[5/7] Generating wordmark logos (light + dark)...")
    generate_wordmark_logos(master)

    print("[6/7] Generating GitHub Banner & Social Preview...")
    generate_github_banner(master)
    generate_social_preview(master)

    print("[7/7] Distributing to extensions & website...")
    distribute_icons()
    cleanup_legacy_files()

    print("=" * 60)
    print("  [DONE] All DLite branding assets generated successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
