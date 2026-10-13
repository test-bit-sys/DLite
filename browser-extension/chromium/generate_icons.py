"""
Generate professional icons for DLite Chrome/Firefox extension.
Creates 16x16, 48x48, and 128x128 PNG icons with a modern download-arrow design.
"""
import math
from PIL import Image, ImageDraw, ImageFont

SIZES = [16, 48, 128]
OUTPUT_DIR = "icons"

# Color palette — modern blue gradient
BG_COLOR = (26, 115, 232)        # Rich blue (#1a73e8)
BG_DARK = (17, 85, 175)          # Darker blue for depth
ARROW_COLOR = (255, 255, 255)    # White arrow
ARROW_SHADOW = (13, 71, 145)     # Shadow on the arrow

def create_icon(size):
    """Create a single icon at the given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── Background: rounded square with subtle gradient ──
    margin = max(1, size * 0.06)
    radius = max(1, size * 0.18)

    # Draw rounded rectangle background
    bg_box = [margin, margin, size - margin, size - margin]

    # Gradient fill (top-to-bottom)
    for y in range(int(bg_box[1]), int(bg_box[3])):
        ratio = (y - bg_box[1]) / (bg_box[3] - bg_box[1])
        r = int(BG_COLOR[0] + (BG_DARK[0] - BG_COLOR[0]) * ratio)
        g = int(BG_COLOR[1] + (BG_DARK[1] - BG_COLOR[1]) * ratio)
        b = int(BG_COLOR[2] + (BG_DARK[2] - BG_COLOR[2]) * ratio)
        draw.rectangle(
            [bg_box[0], y, bg_box[2], y + 1],
            fill=(r, g, b),
        )

    # Rounded corners — cover corners with transparent circles
    r_corner = int(radius)
    for cx, cy in [
        (bg_box[0] + r_corner, bg_box[1] + r_corner),
        (bg_box[2] - r_corner, bg_box[1] + r_corner),
        (bg_box[0] + r_corner, bg_box[3] - r_corner),
        (bg_box[2] - r_corner, bg_box[3] - r_corner),
    ]:
        for x in range(int(cx - r_corner), int(cx + r_corner) + 1):
            for y in range(int(cy - r_corner), int(cy + r_corner) + 1):
                dx, dy = x - cx, y - cy
                if math.sqrt(dx * dx + dy * dy) > r_corner:
                    if 0 <= x < size and 0 <= y < size:
                        if (
                            (cx < size / 2 and cy < size / 2)
                            or (cx > size / 2 and cy < size / 2)
                            or (cx < size / 2 and cy > size / 2)
                            or (cx > size / 2 and cy > size / 2)
                        ):
                            # Check if pixel is outside the corner circle
                            pass  # We'll handle this differently below

    # Better rounded corners: create a mask
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=255,
    )

    # Apply gradient to the mask area
    for y in range(int(bg_box[1]), int(bg_box[3])):
        ratio = (y - bg_box[1]) / (bg_box[3] - bg_box[1])
        r_val = int(BG_COLOR[0] + (BG_DARK[0] - BG_COLOR[0]) * ratio)
        g_val = int(BG_COLOR[1] + (BG_DARK[1] - BG_COLOR[1]) * ratio)
        b_val = int(BG_COLOR[2] + (BG_DARK[2] - BG_COLOR[2]) * ratio)
        for x in range(int(bg_box[0]), int(bg_box[2])):
            if mask.getpixel((x, y)):
                img.putpixel((x, y), (r_val, g_val, b_val, 255))

    # ── Download arrow ──
    arrow_width = size * 0.45
    arrow_height = size * 0.50
    arrow_stroke = max(2, size * 0.08)

    cx = size / 2
    # Arrow vertical area from ~35% to ~80% of height
    top_y = size * 0.28
    bottom_y = size * 0.75

    # Arrow shaft (vertical line)
    shaft_x = cx
    shaft_top = top_y
    shaft_bottom = bottom_y - arrow_stroke * 0.8
    shaft_thickness = arrow_stroke * 0.65

    # Draw shaft
    for y in range(int(shaft_top), int(shaft_bottom)):
        for x in range(int(shaft_x - shaft_thickness), int(shaft_x + shaft_thickness)):
            if 0 <= x < size and 0 <= y < size and mask.getpixel((x, y)):
                img.putpixel((x, y), (*ARROW_COLOR, 255))

    # Arrow head (triangle pointing down)
    head_width = arrow_width * 0.9
    head_height = arrow_stroke * 2.0
    head_left = cx - head_width / 2
    head_right = cx + head_width / 2
    head_top_y = shaft_bottom
    head_bottom_y = bottom_y

    # Draw arrow head as a filled triangle
    for y in range(int(head_top_y), int(head_bottom_y)):
        progress = (y - head_top_y) / max(1, (head_bottom_y - head_top_y))
        half_width = (head_width / 2) * progress
        left_x = cx - half_width
        right_x = cx + half_width
        for x in range(int(left_x), int(right_x) + 1):
            if 0 <= x < size and 0 <= y < size and mask.getpixel((x, y)):
                img.putpixel((x, y), (*ARROW_COLOR, 255))

    # ── Horizontal base bar below arrow ──
    bar_y = bottom_y + arrow_stroke * 0.6
    bar_width = arrow_width * 0.7
    bar_height = max(1, arrow_stroke * 0.45)
    bar_left = cx - bar_width / 2

    for y in range(int(bar_y - bar_height / 2), int(bar_y + bar_height / 2) + 1):
        for x in range(int(bar_left), int(bar_left + bar_width)):
            if 0 <= x < size and 0 <= y < size and mask.getpixel((x, y)):
                img.putpixel((x, y), (*ARROW_COLOR, 255))

    # ── Small dots on the left and right of the bar ──
    dot_radius = max(1, int(bar_height * 1.2))
    for side in [-1, 1]:
        dx = int(bar_left + bar_width * (0.15 if side == -1 else 0.85))
        dy = int(bar_y)
        for x in range(dx - dot_radius, dx + dot_radius + 1):
            for y in range(dy - dot_radius, dy + dot_radius + 1):
                if (x - dx) ** 2 + (y - dy) ** 2 <= dot_radius ** 2:
                    if 0 <= x < size and 0 <= y < size and mask.getpixel((x, y)):
                        img.putpixel((x, y), (*ARROW_COLOR, 255))

    return img


def main():
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for size in SIZES:
        icon = create_icon(size)
        path = os.path.join(OUTPUT_DIR, f"icon{size}.png")
        icon.save(path, "PNG")
        print(f"  ✓ Created {path} ({size}x{size})")

    # Also save as icon.png (128px) for general use
    icon128 = create_icon(128)
    path = os.path.join(OUTPUT_DIR, "icon.png")
    icon128.save(path, "PNG")
    print(f"  ✓ Created {path} (128x128)")

    print("\nDone! Icons saved to browser-extension/chromium/icons/")
    print("Copy these icons to the firefox extension folder as well.")


if __name__ == "__main__":
    main()