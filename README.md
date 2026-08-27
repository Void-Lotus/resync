# resync - Arch Linux System Replicator & Dotfile Sync Engine

**resync** is a modern, modular system replicator and dotfile management engine designed for Arch Linux and Arch-based distros (CachyOS, EndeavourOS, pure Arch).

It was built from the ground up to replace GNU Stow with direct file templating, source-compiled AUR tooling, hardware auto-probing, and bidirectional synchronization across multiple machines.

---

## Key Improvements Over Legacy Stow Installers

| Feature | Legacy Installer (Stow) | **resync** |
| :--- | :--- | :--- |
| **Dotfile Strategy** | Fragile directory symlinks (breaks on app atomic renames) | **Direct copy with automatic backups & templating (Zero broken symlinks)** |
| **AUR Helper (`paru`)** | Downloaded `paru-bin` (breaks when `libalpm` updates) | **Strictly compiled from source (`aur.archlinux.org/paru.git`)** |
| **Multi-Laptop Support** | Hardcoded variables (`BAT0`, static hostname) | **Auto-probes CPU, GPU, Battery (`BAT1`/`BAT0`), Backlight, and Hostname** |
| **Synchronization** | One-time install only | **`./setup.sh sync` (pull updates) & `./setup.sh collect` (push edits to repo)** |
| **Inspection & Safety** | Destructive overwrites | **`./setup.sh diff` (preview changes) & `./setup.sh rollback` (restore snapshot)** |

---

## Directory Structure

```text
resync/
├── setup.sh                     # Fast runner script (auto-detects python and permissions)
├── resync.py                    # Main orchestrator CLI & TUI engine
├── core/
│   ├── hardware.py              # Probes CPU, GPU, Battery, Backlight, Distro & Chassis
│   ├── aur.py                   # Compiles paru directly from source
│   ├── packages.py              # Pacman & Paru package manager with parallel downloads
│   ├── dotfiles.py              # Direct copy engine, diff inspector, and backups
│   ├── system.py                # Hostname setup, /etc/hosts, systemd services, shell
│   ├── display_manager.py       # Noctalia Greeter (greetd) & SDDM setup
│   └── cac.py                   # DoD CAC / Smart Card configuration
├── manifests/                   # Package lists
│   ├── core.txt                 # Essential base utilities
│   ├── wm-umbriel.txt           # Umbriel Compositor & dependencies
│   ├── wm-hyprland.txt          # Hyprland ecosystem
│   ├── wm-niri.txt              # Niri Compositor
│   ├── shell.txt                # Shell, starship, fastfetch, fzf, lsd
│   └── optional-*.txt           # Browsers, dev tools, fonts, media, CAC
└── configs/
    ├── home/                    # Direct dotfiles targeting $HOME (~/.config, .zshrc, .local/bin)
    └── system/                  # System-level configs (noctalia-greeter, sddm)
```

---

## How to Use

### 1. Fresh Machine Installation
On any fresh Arch Linux or CachyOS installation:
```bash
git clone <your-resync-repo-url> ~/Projects/resync
cd ~/Projects/resync
./setup.sh
```
The interactive wizard will:
1. Probe hardware (CPU, GPU, battery, backlight).
2. Prompt for your custom **Hostname** (e.g. `thinkpad-x1`, `glitchlotus`).
3. Allow choosing your Window Manager (**Umbriel**, **Hyprland**, or **Niri**).
4. Allow choosing your Display Manager (**Noctalia Greeter** or **SDDM**).
5. Compile `paru` from source to prevent library breakage.
6. Install official Pacman and AUR packages.
7. Deploy all dotfiles, shell configs, wallpapers, and fonts directly into `$HOME`.
8. Enable systemd services and set default shell to Zsh.

---

### 2. Multi-Laptop Daily Synchronization

#### A. Apply Latest Configs to Current Laptop
Whenever you make updates in your repo and want this laptop to match:
```bash
./setup.sh sync
```

#### B. Inspect Differences Before Applying
```bash
./setup.sh diff
```

#### C. Collect Live Changes Back into the Repo
If you customized your `.zshrc`, Noctalia config, or keybindings on one laptop and want to commit them to git:
```bash
./setup.sh collect
git add .
git commit -m "Update configs"
git push
```

#### D. Rollback to a Previous Snapshot
If you ever want to revert dotfile changes:
```bash
./setup.sh rollback
```

#### E. View Hardware & Sensor Probe
```bash
./setup.sh hardware
```

---

## Template Placeholders

Configs in `configs/home/` support dynamic templating:
* `{{HOME}}`: Real home directory (e.g. `/home/voidlotus`).
* `{{USER}}`: Current non-root username.
* `{{HOSTNAME}}`: Current or newly configured hostname.
* `{{BATTERY}}`: Auto-detected primary battery sensor (`BAT0`, `BAT1`, etc.).
* `{{BACKLIGHT}}`: Auto-detected backlight controller (`amdgpu_bl1`, `intel_backlight`).
* `{{SCALE}}`: Display scale factor.
