#!/usr/bin/env python3
"""
generate_greeter_wallpaper.py
Generates a composite wallpaper for Noctalia Greeter where the overall
image is 100% crisp and sharp, but the area directly behind the login card
has a smooth Gaussian blur (frosted glass effect).
"""

import os
import sys
import glob
from PIL import Image, ImageFilter, ImageDraw

def get_screen_resolution():
    default_w, default_h = 1920, 1200
    try:
        modes_files = glob.glob("/sys/class/drm/*-eDP-1/modes") or glob.glob("/sys/class/drm/*/modes")
        if modes_files:
            with open(modes_files[0], "r") as f:
                first_line = f.readline().strip()
                if "x" in first_line:
                    w_s, h_s = first_line.split("x", 1)
                    return int(w_s), int(h_s)
    except Exception:
        pass
    return default_w, default_h

def find_active_wallpaper():
    settings_file = os.path.expanduser("~/.local/state/noctalia/settings.toml")
    if os.path.isfile(settings_file):
        try:
            with open(settings_file, "r") as f:
                in_last = False
                for line in f:
                    line = line.strip()
                    if line.startswith("[wallpaper.last]"):
                        in_last = True
                        continue
                    elif line.startswith("["):
                        in_last = False
                    if in_last and line.startswith("path"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            p = parts[1].strip().strip('"').strip("'")
                            if os.path.isfile(p):
                                return p
        except Exception:
            pass

    candidates = [
        os.path.expanduser("~/Pictures/wallpapers/Green Void Lotus.png"),
        os.path.expanduser("~/Pictures/wallpapers/GlitchLotus.png"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def generate_frosted_wallpaper(input_path, output_path, target_w=None, target_h=None):
    if not target_w or not target_h:
        target_w, target_h = get_screen_resolution()

    img = Image.open(input_path).convert("RGBA")

    # Fit / Crop image to target screen resolution
    aspect_target = target_w / target_h
    aspect_img = img.width / img.height

    if aspect_img > aspect_target:
        new_h = target_h
        new_w = int(img.width * (target_h / img.height))
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        img_fitted = img_resized.crop((left, 0, left + target_w, target_h))
    else:
        new_w = target_w
        new_h = int(img.height * (target_w / img.width))
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        top = (new_h - target_h) // 2
        img_fitted = img_resized.crop((0, top, target_w, top + target_h))

    # Generate Gaussian blurred version (radius 32 for frosted glass)
    blurred = img_fitted.filter(ImageFilter.GaussianBlur(radius=32))

    # Create mask for the login card area
    mask = Image.new("L", (target_w, target_h), 0)
    draw = ImageDraw.Draw(mask)

    # Card dimensions in Noctalia Greeter (center aligned)
    card_w = min(int(target_w * 0.32), 540)
    card_w = max(card_w, 460)
    card_h = 580

    cx, cy = target_w // 2, target_h // 2
    x0 = cx - card_w // 2
    y0 = cy - card_h // 2
    x1 = cx + card_w // 2
    y1 = cy + card_h // 2

    # Draw rounded rectangle mask
    draw.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=255)

    # Soft feathering on the mask edges
    mask_feathered = mask.filter(ImageFilter.GaussianBlur(radius=10))

    # Composite: crisp background everywhere, Gaussian blur in the card area
    composite = Image.composite(blurred, img_fitted, mask_feathered)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    composite.save(output_path, "PNG")
    print(f"[✓] Frosted greeter wallpaper generated: {output_path} ({target_w}x{target_h})")

def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else find_active_wallpaper()
    output_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/noctalia_greeter_wallpaper.png"

    if not input_path or not os.path.isfile(input_path):
        print(f"Error: Wallpaper file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    generate_frosted_wallpaper(input_path, output_path)

if __name__ == "__main__":
    main()
