#!/usr/bin/env bash

# Set layout to ribbon / scrolling and notify via Noctalia
umbriel msg workspace-set-layout:scrolling
noctalia msg notification-show "Workspace Layout" "--" "Ribbon / Scrolling Tiling Mode Activated"
