# 🔄 resync

> **A modern, symlink-free system replicator and dotfile synchronization engine for Arch Linux & CachyOS.**

Born out of the frustration of broken symlinks, mismatched laptop sensors, and repetitive post-install setups. **`resync`** takes a fresh Arch-based installation and transforms it into your exact, fully customized desktop in one command.

---

## 💡 The Story Behind `resync`

Like many Linux enthusiasts who bounce between multiple laptops and desktops, I relied on **GNU Stow** for years to manage my dotfiles. But in the real world of modern desktop apps, atomic file writes, and multi-machine setups, symlinks constantly break. An editor re-saves a file and suddenly detaches the symlink, or you pull dotfiles on a different laptop and your battery indicators fail because one machine uses `BAT0` and another uses `BAT1`.

I wanted something cleaner, smarter, and bulletproof:
1. **No fragile symlinks.** Copy real, templated files directly into `$HOME`, with automatic timestamped backups before anything gets touched.
2. **Build critical tools from source.** Build `paru` and `umbriel` directly with Rust and C++23 Meson so upstream `pacman` library bumps (`libalpm.so`) never break your system.
3. **Multi-laptop intelligence.** Automatically probe CPU microcode, GPU drivers, battery sensors, and backlight controllers, while letting you customize your hostname on the fly.
4. **Thumbdrive-ready portability.** Plug in a USB drive on a freshly installed laptop, `cd` into it, run `./setup.sh`, and be up and running with all 197 wallpapers and configs without waiting on multi-gigabyte downloads.
5. **Two-way synchronization.** Tweak an alias or theme on one laptop, `collect` it back into the repo, push to GitHub, and run `sync` on your other machines.

---

## ✨ Key Features

* 🪟 **First-Class Wayland Compositor Ecosystem**:
  * **Umbriel**: Automated source build directly from the official [noctalia-dev/umbriel](https://github.com/noctalia-dev/umbriel) repository with SceneFX submodules.
  * **Hyprland** & **Niri**: Dynamic tiling and scrollable tiling presets.
* 🎨 **Complete Desktop Shell & Theme Suite**:
  * Noctalia desktop shell integration with Noctalia Greeter (`greetd`) and frosted blur.
  * Includes 197 curated wallpapers, GTK themes, and Bibata/Flat-Remix icon sets.
* ⚡ **Zero Broken Symlinks (Direct Templating Engine)**:
  * Deploys clean real files to `~/.config/`, `~/.local/bin/`, and `$HOME`.
  * Dynamic template tags: `{{HOME}}`, `{{USER}}`, `{{HOSTNAME}}`, `{{BATTERY}}`, `{{BACKLIGHT}}`, and `{{SCALE}}`.
* 🛡️ **Safe Backups, Diffs & Rollbacks**:
  * Every single deployment automatically snapshots previous files into `~/.local/state/resync/backups/<timestamp>/`.
  * Built-in colorized unified diff inspector (`./setup.sh diff`) and generation rollback (`./setup.sh rollback`).
* 💻 **Hardware Auto-Detection**:
  * Detects CPU vendor (`intel-ucode` vs `amd-ucode`), GPU (`nvidia-open`, `vulkan-radeon`, `vulkan-intel`), and laptop power sensors.
* 💳 **DoD CAC / Smart Card Support**:
  * Automated `pcscd` daemon setup and OpenSC PKCS#11 browser registration for secure smart card login.

---

## 🚀 Quick Start

### Method 1: Clean Install via Git
On any fresh Arch Linux, CachyOS, or EndeavourOS machine:

```bash
# 1. Clone the repository
git clone https://github.com/Void-Lotus/resync.git ~/Projects/resync
cd ~/Projects/resync

# 2. Launch the interactive installer
./setup.sh
```

---

### Method 2: Running Directly from a USB Thumbdrive 💾
No need to wait for 1 GB of wallpapers to download over Wi-Fi! Keep `resync` on a flash drive:

```bash
# 1. Plug in your USB and open terminal in the mounted drive
cd /run/media/$USER/YOUR_USB/resync

# 2. Run the installer
./setup.sh
```
`resync` is completely path-independent. It automatically resolves the target laptop's `$HOME` and copies everything over cleanly.

---

## 🔁 Multi-Laptop Daily Synchronization

Whenever you customize a config or add a new alias, keep all your laptops in perfect harmony:

### On the machine where you made changes:
```bash
cd ~/Projects/resync

# 1. Pull your live changes from $HOME back into the repository
./setup.sh collect

# 2. Push to GitHub
git commit -am "Tweak keybindings and waybar layout"
git push
```

### On your other laptops:
```bash
cd ~/Projects/resync

# 1. Pull latest updates from GitHub
git pull

# 2. Deploy them to this laptop's $HOME
./setup.sh sync
```

---

## 🛠️ Command Reference

| Command | What It Does |
| :--- | :--- |
| **`./setup.sh`** | Launches the full interactive setup wizard on a fresh machine. |
| **`./setup.sh sync`** | Quickly renders templates and deploys repo configs to `$HOME` (with automatic backups). |
| **`./setup.sh diff`** | Shows a colorized unified diff comparing your live `$HOME` against the repository. |
| **`./setup.sh collect`** | Copies modified configs from live `$HOME` back into the repo so you can `git push`. |
| **`./setup.sh rollback`** | Interactive menu to restore previous dotfile generations from backup snapshots. |
| **`./setup.sh hardware`** | Displays detected CPU, GPU, Battery devices (`BAT0`/`BAT1`), Backlight, and Chassis info. |

---

## 📂 Project Structure

```text
resync/
├── setup.sh                     # Fast runner script (auto-detects python & dependencies)
├── resync.py                    # Main orchestrator CLI & modern terminal UI
├── core/
│   ├── hardware.py              # Probes CPU, GPU, Battery, Backlight, Distro & Chassis
│   ├── aur.py                   # Compiles paru strictly from source
│   ├── sources.py               # Compiles Umbriel compositor from official GitHub source
│   ├── packages.py              # Pacman & Paru package manager with parallel downloads
│   ├── dotfiles.py              # Direct templating, diff inspector, and backup engine
│   ├── system.py                # Hostname configuration, /etc/hosts, systemd services
│   ├── display_manager.py       # Noctalia Greeter (greetd) & SDDM setup
│   └── cac.py                   # DoD CAC smart card configuration
├── manifests/                   # Categorized package lists
│   ├── core.txt                 # Essential base utilities
│   ├── wm-umbriel.txt           # Umbriel & Noctalia shell dependencies
│   ├── wm-hyprland.txt          # Hyprland ecosystem
│   ├── wm-niri.txt              # Niri compositor
│   ├── shell.txt                # Shell, starship, fastfetch, lsd, fzf, bat
│   └── optional-*.txt           # Browsers, dev tools, fonts, media, CAC
└── configs/
    ├── home/                    # Direct dotfiles targeting $HOME (~/.config, .zshrc, .local/bin)
    │   ├── .config/ (noctalia, umbriel, hypr, waybar, alacritty, ghostty, kitty, etc.)
    │   ├── Pictures/wallpapers/ # All 197 wallpapers
    │   └── .zshrc, .bashrc, .local/bin/
    └── system/                  # System configs (noctalia-greeter, sddm)
```

---

## 📜 License & Acknowledgments

Created and maintained with ❤️ by [Void-Lotus](https://github.com/Void-Lotus).

Special thanks to the [Noctalia Dev Team](https://github.com/noctalia-dev) for Umbriel & Noctalia, and the Arch Linux / CachyOS communities.
