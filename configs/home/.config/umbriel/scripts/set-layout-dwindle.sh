#!/usr/bin/env bash

# Set layout to dwindle and notify via Noctalia
umbriel msg workspace-set-layout:dwindle
noctalia msg notification-show "Workspace Layout" "--" "Dwindle Layout Activated"
