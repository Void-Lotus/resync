#!/usr/bin/env bash

STATE_FILE="${XDG_RUNTIME_DIR:-/tmp}/umbriel_layout_mode"

# Default mode from config is scrolling
CURRENT_MODE="scrolling"
if [ -f "$STATE_FILE" ]; then
    CURRENT_MODE=$(cat "$STATE_FILE")
fi

if [ "$CURRENT_MODE" = "scrolling" ]; then
    NEXT_MODE="dwindle"
    BODY="Dwindle Layout Activated"
else
    NEXT_MODE="scrolling"
    BODY="Ribbon / Scrolling Tiling Mode Activated"
fi

# Set layout explicitly and record state
umbriel msg workspace-set-layout:"$NEXT_MODE"
echo "$NEXT_MODE" > "$STATE_FILE"

# Send Noctalia pop-up notification
noctalia msg notification-show "Workspace Layout" "--" "$BODY"
