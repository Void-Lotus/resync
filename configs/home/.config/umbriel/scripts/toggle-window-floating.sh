#!/usr/bin/env bash

# Toggle active window floating state in Umbriel
umbriel msg window-toggle-floating

# Short pause for compositor state update
sleep 0.05

# Inspect focused window state from umbriel output
FOCUSED_WIN=$(umbriel windows 2>/dev/null | grep '^\*')

if echo "$FOCUSED_WIN" | grep -q '\[float'; then
    noctalia msg notification-show "Window Mode" "--" "Floating Mode Activated"
else
    noctalia msg notification-show "Window Mode" "--" "Tiling / Ribbon Mode Activated"
fi
