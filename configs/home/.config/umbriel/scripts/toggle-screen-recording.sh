#!/usr/bin/env bash

# Toggle screen recording script for Umbriel
SAVE_DIR="$HOME/Videos/Recordings"
mkdir -p "$SAVE_DIR"

if pgrep -x "wf-recorder" > /dev/null; then
    # Stop recording cleanly
    pkill -INT -x "wf-recorder"
    sleep 0.5
    noctalia msg notification-show "Screen Recording" "--" "Recording Stopped & Saved to ~/Videos/Recordings"
else
    # Start recording
    TIMESTAMP=$(date +'%Y-%m-%d_%H-%M-%S')
    FILE_PATH="$SAVE_DIR/recording_${TIMESTAMP}.mp4"
    
    # Run wf-recorder (video only) in background
    wf-recorder -f "$FILE_PATH" >/dev/null 2>&1 &
    
    sleep 0.2
    if pgrep -x "wf-recorder" > /dev/null; then
        noctalia msg notification-show "Screen Recording" "--" "Recording Started... Press keybind again to stop"
    else
        noctalia msg notification-show "Screen Recording" "--" "Failed to start recording"
    fi
fi
