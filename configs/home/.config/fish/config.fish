source /usr/share/cachyos-fish-config/cachyos-config.fish

# Overwrite greeting to use compact/small fastfetch
function fish_greeting
    fastfetch -c ~/.config/fastfetch/config-compact.jsonc
end

