#!/bin/bash
# Toggle Apple Internal Trackpad in Hyprland

DEVICE="apple-inc.-apple-internal-keyboard-/-trackpad-1"
STATUS_FILE="/tmp/trackpad_status"

# If the status file doesn't exist, assume trackpad is enabled
if [ ! -f "$STATUS_FILE" ] || [ "$(cat "$STATUS_FILE")" = "true" ]; then
    hyprctl keyword "device[$DEVICE]:enabled" false
    echo "false" > "$STATUS_FILE"
    notify-send -t 1500 -a "System" "Trackpad" "Disabled 🚫" -i input-touchpad
else
    hyprctl keyword "device[$DEVICE]:enabled" true
    echo "true" > "$STATUS_FILE"
    notify-send -t 1500 -a "System" "Trackpad" "Enabled 🟢" -i input-touchpad
fi
