#!/usr/bin/env bash
# /* ---- 💫 https://github.com/Void-Lotus 💫 ---- */  ##

# GDK BACKEND. Change to either wayland or x11 if having issues
BACKEND=wayland

# Check if rofi or yad is running and kill them if they are
if pidof rofi > /dev/null; then
  pkill rofi
fi

if pidof yad > /dev/null; then
  pkill yad
fi

# Launch yad with calculated width and height
GDK_BACKEND=$BACKEND yad \
    --center \
    --title="VoidLotus Quick Cheat Sheet" \
    --no-buttons \
    --list \
    --column=Key: \
    --column=Description: \
    --column=Command: \
    --timeout-indicator=bottom \
"ESC" "close this app" "" " = " "SUPER KEY (Windows Key Button)" "(SUPER KEY)" \
" SHIFT K" "Searchable Keybinds" "(Search all Keybinds via rofi)" \
" SHIFT E" "VoidLotus Hyprland Settings Menu" "" \
"" "" "" \
" enter" "Terminal" "(kitty)" \
" SHIFT enter" "Open File Manager" "(Thunar)" \
" B" "Launch Browser" "(Default browser)" \
" A" "Open Assistant Panel" "(noctalia assistant)" \
" D" "Open App Launcher" "(noctalia launcher)" \
" E" "Open File Manager" "(Thunar)" \
" S" "Open Settings Panel" "(noctalia settings)" \
" T" "Global theme switcher" "(rofi)" \
" Q" "close active window" "(not kill)" \
" Shift Q" "Session Menu" "(noctalia sessionMenu)" \
" SHIFT J" "Launch Joplin" "(kitty -e joplin)" \
" C" "Open agy" "(kitty -e agy)" \
" ALT mouse scroll up/down" "Desktop Zoom" "Desktop Magnifier" \
" Alt V" "Clipboard Manager" "(cliphist)" \
" W" "Open Zen Browser" "(zen-browser)" \
" Shift W" "Open Google Chrome" "(google-chrome)" \
" /" "Choose wallpaper" "(Wallpaper Menu)" \
" Shift /" "Choose wallpaper effects" "(awww + wallust)" \
"CTRL ALT W" "Random wallpaper" "(via awww)" \
" CTRL ALT B" "Hide/UnHide Waybar" "waybar" \
" CTRL B" "Choose waybar styles" "(waybar styles)" \
" ALT B" "Choose waybar layout" "(waybar layout)" \
" ALT R" "Reload Waybar swaync Rofi" "CHECK NOTIFICATION FIRST!!!" \
" SHIFT N" "Launch Notification Panel" "swaync Notification Center" \
" Print" "screenshot" "(grim)" \
" Shift Print" "screenshot region" "(grim + slurp)" \
" Shift S" "screenshot region" "(swappy)" \
" CTRL Print" "screenshot timer 5 secs " "(grim)" \
" CTRL SHIFT Print" "screenshot timer 10 secs " "(grim)" \
"ALT Print" "Screenshot active window" "active window only" \
"CTRL ALT P" "Powermenu" "(noctalia sessionMenu)" \
"CTRL ALT L" "Lock Screen" "(noctalia lock)" \
"CTRL ALT Del" "Hyprland Exit" "(NOTE: Hyprland Will exit immediately)" \
" SHIFT F" "Fullscreen" "Toggles to full screen" \
" CTL F" "Fake Fullscreen" "Toggles to fake full screen" \
" ALT L" "Toggle Dwindle | Master Layout" "Hyprland Layout" \
" SPACEBAR" "Toggle float" "single window" \
" ALT SPACEBAR" "Toggle all windows to float" "all windows" \
" ALT O" "Toggle Blur" "normal or less blur" \
" CTRL O" "Toggle Opaque ON or OFF" "on active window only" \
" Shift A" "Animations Menu" "Choose Animations via rofi" \
" CTRL R" "Rofi Themes Menu" "Choose Rofi Themes via rofi" \
" CTRL Shift R" "Rofi Themes Menu v2" "Choose Rofi Themes via Theme Selector (modified)" \
" SHIFT G" "Gamemode! All animations OFF or ON" "toggle" \
" ALT E" "Rofi Emoticons" "Emoticon" \
" H" "Launch this Quick Cheat Sheet" "" \
"" "" "" \
"More tips:" "https://github.com/Void-Lotus/Hyprland-Dots/wiki" ""

