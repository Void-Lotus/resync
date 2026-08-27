#!/usr/bin/env python3
import time
import math
import subprocess
import os

BORDER_THEME_PATH = os.path.expanduser("~/.config/umbriel/border-theme.toml")

def lerp(a, b, t):
    return a + (b - a) * t

def color_hex(r, g, b, a=255):
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}{int(a):02X}"

def main():
    t = 0.0
    last_content = ""

    while True:
        phase = 0.5 + 0.5 * math.sin(t)

        r_f = lerp(0x2F, 0x10, phase)
        g_f = lerp(0x67, 0xF0, phase)
        b_f = lerp(0x44, 0xA0, phase)
        border_focused = color_hex(r_f, g_f, b_f)

        r_s = lerp(0x5F, 0x00, phase)
        g_s = lerp(0xA1, 0xFF, phase)
        b_s = lerp(0x72, 0xD0, phase)
        scratchpad_focused = color_hex(r_s, g_s, b_s)

        content = f"""[appearance]
border_focused = "{border_focused}"
scratchpad_border_focused = "{scratchpad_focused}"
scratchpad_border_unfocused = "#2F674480"
"""

        if content != last_content:
            with open(BORDER_THEME_PATH, "w") as f:
                f.write(content)
            subprocess.run(["umbriel", "msg", "config-reload"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            last_content = content

        t += 0.15
        time.sleep(0.12)

if __name__ == '__main__':
    main()
