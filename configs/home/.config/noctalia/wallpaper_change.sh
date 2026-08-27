#!/usr/bin/env bash
# Script triggered by Noctalia when wallpaper changes

set -euo pipefail

export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

# 1. Read current wallpaper path
wallpaper_path="${1:-${NOCTALIA_WALLPAPER_PATH:-}}"
if [ -z "$wallpaper_path" ]; then
    settings_file="$HOME/.local/state/noctalia/settings.toml"
    if [ -f "$settings_file" ]; then
        wallpaper_path=$(awk -F'"' '/\[wallpaper\.last\]/{flag=1;next} /^\[/{flag=0} flag && /path/{print $2; exit}' "$settings_file")
        if [ -z "$wallpaper_path" ]; then
            wallpaper_path=$(awk -F'"' '/\[wallpaper\.default\]/{flag=1;next} /^\[/{flag=0} flag && /path/{print $2; exit}' "$settings_file")
        fi
    fi
fi

if [ -z "$wallpaper_path" ] || [ ! -f "$wallpaper_path" ]; then
    echo "Could not find a valid wallpaper path: $wallpaper_path" >&2
    exit 1
fi

echo "Active wallpaper: $wallpaper_path"

# 2. Run Wallust to update Wallust templates
if command -v wallust >/dev/null 2>&1; then
    echo "Running Wallust..."
    for file in "$HOME/.config/rofi/wallust/colors-rofi.rasi" \
                "$HOME/.config/kitty/kitty-themes/01-Wallust.conf" \
                "$HOME/.config/cava/config" \
                "$HOME/.config/ghostty/wallust.conf" \
                "$HOME/.config/alacritty/themes/wallust.toml" \
                "$HOME/.config/umbriel/noctalia.toml"; do
        if [ -L "$file" ]; then
            rm -f "$file"
        fi
    done
    wallust run "$wallpaper_path" || true
    
    # Sync Kitty current theme & reload if Kitty is running
    if [ -f "$HOME/.config/kitty/kitty-themes/01-Wallust.conf" ]; then
        cp -f "$HOME/.config/kitty/kitty-themes/01-Wallust.conf" "$HOME/.config/kitty/current-theme.conf" 2>/dev/null || true
        pkill -USR1 kitty 2>/dev/null || true
    fi
else
    echo "Wallust command not found (using Noctalia theming)." >&2
fi

# Reload Umbriel window manager config
if command -v umbriel >/dev/null 2>&1; then
    umbriel msg config-reload 2>/dev/null || true
fi

# 3. Handle SDDM cache if directory exists
sddm_cache="/var/cache/sddm-wallpaper"
if [ -d "$sddm_cache" ]; then
    # 4. Copy wallpaper and generate blurred version for SDDM
    echo "Generating blurred wallpaper for SDDM..."
    cp -f "$wallpaper_path" "$sddm_cache/background.png" 2>/dev/null || true
    chmod 644 "$sddm_cache/background.png" 2>/dev/null || true

    # Generate Gaussian blurred version
    if command -v magick >/dev/null 2>&1; then
        magick "$wallpaper_path" -resize 1920x1080^ -gravity center -extent 1920x1080 -blur 0x30 "$sddm_cache/background_blurred.png" 2>/dev/null || true
        chmod 644 "$sddm_cache/background_blurred.png" 2>/dev/null || true
    else
        cp -f "$wallpaper_path" "$sddm_cache/background_blurred.png" 2>/dev/null || true
        chmod 644 "$sddm_cache/background_blurred.png" 2>/dev/null || true
    fi

    # 5. Extract colors from Wallust and write theme.conf for SDDM
    rofi_wallust="$HOME/.config/rofi/wallust/colors-rofi.rasi"

    if [ -f "$rofi_wallust" ]; then
        extract_color() {
            local key="$1"
            grep -oP "$key:\s*\K#[A-Fa-f0-9]+" "$rofi_wallust" | head -n1 || echo "#ffffff"
        }

        color0=$(extract_color "color1")
        color1=$(extract_color "color0")
        color7=$(extract_color "color14")
        color10=$(extract_color "color10")
        color12=$(extract_color "color12")
        color13=$(extract_color "color13")
        foreground=$(extract_color "foreground")

        [ -z "$color0" ] && color0="#ffffff"
        [ -z "$color1" ] && color1="#1e1e2e"
        [ -z "$color7" ] && color7="#a6adc8"
        [ -z "$color10" ] && color10="#11111b"
        [ -z "$color12" ] && color12="#89b4fa"
        [ -z "$color13" ] && color13="#cdd6f4"

        cat <<EOF > "$sddm_cache/theme.conf"
[General]
ScreenWidth="1920"
ScreenHeight="1080"
ScreenPadding=""
FontSize="13"
KeyboardSize="0.4"
RoundCorners="20"
Locale=""
HourFormat="HH:mm"
DateFormat="dddd d MMMM"
HeaderText=""
BackgroundPlaceholder=""
Background="/var/cache/sddm-wallpaper/background.png"
BackgroundSpeed=""
PauseBackground=""
DimBackground="0.0"
CropBackground="true"
BackgroundHorizontalAlignment="center"
BackgroundVerticalAlignment="center"

HeaderTextColor="$color13"
DateTextColor="$color13"
TimeTextColor="$color13"
FormBackgroundColor="$color1"
BackgroundColor="$color1"
DimBackgroundColor="$color1"
LoginFieldBackgroundColor="$color1"
PasswordFieldBackgroundColor="$color1"
LoginFieldTextColor="$color12"
PasswordFieldTextColor="$color12"
UserIconColor="$color7"
PasswordIconColor="$color7"
PlaceholderTextColor="$color7"
WarningColor="#343746"
LoginButtonTextColor="$foreground"
LoginButtonBackgroundColor="$color1"
SystemButtonsIconsColor="$color13"
SessionButtonTextColor="$color13"
VirtualKeyboardButtonTextColor="$color13"
DropdownTextColor="$foreground"
DropdownSelectedBackgroundColor="$color13"
DropdownBackgroundColor="$color1"
HighlightTextColor="$color10"
HighlightBackgroundColor="$color12"
HighlightBorderColor="$color1"
HoverUserIconColor="$color7"
HoverPasswordIconColor="$color7"
HoverSystemButtonsIconsColor="$color13"
HoverSessionButtonTextColor="$color13"
HoverVirtualKeyboardButtonTextColor="$color13"

PartialBlur="true"
FullBlur=""
BlurMax="32"
Blur=""
HaveFormBackground="false"
FormPosition="left"
VirtualKeyboardPosition="center"
HideVirtualKeyboard="false"
HideSystemButtons="false"
HideLoginButton="false"
ForceLastUser="true"
PasswordFocus="true"
HideCompletePassword="true"
AllowEmptyPassword="false"
AllowUppercaseLettersInUsernames="false"
BypassSystemButtonsChecks="false"
RightToLeftLayout="false"
EOF
        chmod 664 "$sddm_cache/theme.conf" 2>/dev/null || true
    fi
fi
