#!/usr/bin/env bash
# /* ---- 💫 https://github.com/JaKooLit 💫 ---- */  ##
# Script for Monitor backlights (if supported) using brightnessctl

iDIR="$HOME/.config/swaync/icons"
notification_timeout=1000
step=10  # INCREASE/DECREASE BY THIS VALUE

# Dynamically find the primary monitor backlight device.
# Prefer common laptop monitor display backlights like intel_backlight, amdgpu_bl0, nouveau_bl0, or acpi_video0 over others like appletb_backlight.
DEVICE=""
for dev in intel_backlight amdgpu_bl0 amdgpu_bl1 nouveau_bl0 acpi_video0; do
    if brightnessctl -d "$dev" info >/dev/null 2>&1; then
        DEVICE="$dev"
        break
    fi
done

# If none of the specific ones are found, find the first backlight device that is NOT appletb_backlight
if [ -z "$DEVICE" ]; then
    for dev in $(brightnessctl -l | grep "Device '" | cut -d"'" -f2); do
        if [[ "$dev" != *"appletb"* ]]; then
            DEVICE="$dev"
            break
        fi
    done
fi

if [ -n "$DEVICE" ]; then
    DEVICE_ARG="-d $DEVICE"
else
    DEVICE_ARG=""
fi

# Get current brightness as an integer (without %)
get_brightness() {
    brightnessctl $DEVICE_ARG -m | cut -d, -f4 | tr -d '%'
}

# Determine the icon based on brightness level
get_icon_path() {
    local brightness=$1
    local level=$(( (brightness + 19) / 20 * 20 ))  # Round up to next 20
    if (( level > 100 )); then
        level=100
    fi
    echo "$iDIR/brightness-${level}.png"
}

# Send notification
send_notification() {
    local brightness=$1
    local icon_path=$2

    notify-send -e \
        -h string:x-canonical-private-synchronous:brightness_notif \
        -h int:value:"$brightness" \
        -u low \
        -i "$icon_path" \
        "Screen" "Brightness: ${brightness}%"
}

# Change brightness and notify
change_brightness() {
    local delta=$1
    local current new icon

    current=$(get_brightness)
    new=$((current + delta))

    # Clamp between 5 and 100
    (( new < 5 )) && new=5
    (( new > 100 )) && new=100

    brightnessctl $DEVICE_ARG set "${new}%"

    icon=$(get_icon_path "$new")
    send_notification "$new" "$icon"
}

# Main
case "$1" in
    "--get")
        get_brightness
        ;;
    "--inc")
        change_brightness "$step"
        ;;
    "--dec")
        change_brightness "-$step"
        ;;
    *)
        get_brightness
        ;;
esac