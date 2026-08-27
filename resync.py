#!/usr/bin/env python3
"""
resync - Modern Arch Linux System Replicator & Dotfile Sync Engine
Created to replace Stow and fragile symlinks with direct templating,
smart hardware detection, source-built paru, source-compiled Umbriel,
and bidirectional sync.
"""

import os
import sys
import shutil
import argparse
import subprocess
from typing import Optional, List

from core.hardware import probe_system, HardwareSummary
from core.aur import is_paru_working, build_paru_from_source
from core.sources import build_umbriel_from_source
from core.packages import PackageManager
from core.dotfiles import DotfileEngine
from core.system import (
    set_system_hostname,
    enable_essential_services,
    configure_user_shell,
    refresh_font_cache
)
from core.display_manager import DisplayManagerHelper
from core.cac import setup_cac_smartcard

# Try importing rich for modern terminal UI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich.syntax import Syntax
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

def print_header(title: str):
    if HAS_RICH:
        console.print(Panel(f"[bold cyan]{title}[/bold cyan]", border_style="bright_blue"))
    else:
        print("=" * 60)
        print(f"   {title}")
        print("=" * 60)

def log_msg(msg: str):
    if HAS_RICH:
        if msg.startswith("[✓]"):
            console.print(f"[bold green]{msg}[/bold green]")
        elif msg.startswith("[!]"):
            console.print(f"[bold yellow]{msg}[/bold yellow]")
        elif msg.startswith("[✗]"):
            console.print(f"[bold red]{msg}[/bold red]")
        elif msg.startswith("[*]"):
            console.print(f"[bold cyan]{msg}[/bold cyan]")
        else:
            console.print(f"[dim]{msg}[/dim]")
    else:
        print(msg)

def cmd_hardware(args):
    """Probe and print hardware and system specifications."""
    print_header("resync - System & Hardware Probe")
    hw = probe_system()

    if HAS_RICH:
        table = Table(title="Hardware & Environment Info", border_style="cyan")
        table.add_column("Property", style="bold white")
        table.add_column("Detected Value", style="bold green")

        table.add_row("Distribution", f"{hw.distro_name} (ID: {hw.distro_id})")
        table.add_row("Hostname", hw.hostname or "Not Set")
        table.add_row("User & Home", f"{hw.username} ({hw.home_dir})")
        table.add_row("CPU", f"{hw.cpu_model} ({hw.cpu_vendor})")
        table.add_row("CPU Microcode", hw.cpu_microcode_pkg or "None required")
        table.add_row("GPU(s)", ", ".join(hw.gpu_vendors) if hw.gpu_vendors else "Generic")
        table.add_row("Suggested GPU Drivers", ", ".join(hw.suggested_gpu_pkgs) if hw.suggested_gpu_pkgs else "None")
        table.add_row("Chassis Type", "Laptop" if hw.is_laptop else "Desktop")
        if hw.is_laptop:
            table.add_row("Battery Sensors", ", ".join(hw.battery_devices) or "None")
            table.add_row("Primary Battery", hw.primary_battery)
            table.add_row("Backlight Controllers", ", ".join(hw.backlight_devices) or "None")
            table.add_row("Primary Backlight", hw.primary_backlight)
        console.print(table)
    else:
        print(f"Distro:          {hw.distro_name} (ID: {hw.distro_id})")
        print(f"Hostname:        {hw.hostname}")
        print(f"User & Home:     {hw.username} ({hw.home_dir})")
        print(f"CPU:             {hw.cpu_model} ({hw.cpu_vendor})")
        print(f"GPU(s):          {', '.join(hw.gpu_vendors)}")
        print(f"Chassis:         {'Laptop' if hw.is_laptop else 'Desktop'}")
        if hw.is_laptop:
            print(f"Batteries:       {', '.join(hw.battery_devices)} (Primary: {hw.primary_battery})")
            print(f"Backlight:       {', '.join(hw.backlight_devices)} (Primary: {hw.primary_backlight})")

def cmd_diff(args):
    """Show differences between repo dotfiles and live $HOME."""
    print_header("resync - Dotfile Diff Inspection")
    hw = probe_system()
    extra_vars = {
        "BATTERY": hw.primary_battery,
        "BACKLIGHT": hw.primary_backlight,
        "HOSTNAME": hw.hostname
    }
    engine = DotfileEngine()
    diffs = engine.diff(extra_vars=extra_vars)

    if not diffs:
        log_msg("[✓] All configurations in $HOME are 100% in sync with repo.")
        return

    log_msg(f"[*] Found {len(diffs)} differences between repo and live $HOME:")
    for item in diffs:
        if HAS_RICH:
            console.print(f"\n[bold yellow]File:[/bold yellow] [bold white]~/{item['path']}[/bold white] ([cyan]{item['status']}[/cyan])")
            if item.get("diff"):
                syntax = Syntax(item['diff'], "diff", theme="monokai", line_numbers=False)
                console.print(syntax)
        else:
            print(f"\nFile: ~/{item['path']} ({item['status']})")
            if item.get("diff"):
                print(item['diff'])

def cmd_sync(args):
    """Quickly synchronize dotfiles and configs from repo to $HOME."""
    print_header("resync - Dotfile Synchronization")
    hw = probe_system()
    extra_vars = {
        "BATTERY": hw.primary_battery,
        "BACKLIGHT": hw.primary_backlight,
        "HOSTNAME": hw.hostname
    }
    engine = DotfileEngine()
    engine.deploy(extra_vars=extra_vars, log_cb=log_msg)
    refresh_font_cache(log_msg)
    log_msg("[✓] Sync completed successfully.")

def cmd_collect(args):
    """Collect modified files from live $HOME back into the repo."""
    print_header("resync - Collect Live Changes into Repo")
    engine = DotfileEngine()
    updated = engine.collect(log_cb=log_msg)
    if updated > 0:
        log_msg(f"[✓] {updated} files updated in repo. You can now run `git commit` and `git push`.")
    else:
        log_msg("[✓] No modified live files found. Repo is already up to date.")

def cmd_rollback(args):
    """Roll back live dotfiles from a previous backup generation."""
    print_header("resync - Generation Rollback")
    engine = DotfileEngine()
    backups = engine.list_backups()

    if not backups:
        log_msg("[!] No backup generations found.")
        return

    print("Available backup snapshots:")
    for idx, b in enumerate(backups, 1):
        print(f" {idx}) {b}")

    choice = input(f"Select backup to restore [1-{len(backups)}]: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(backups):
            selected = backups[idx]
            engine.rollback(selected, log_cb=log_msg)
        else:
            log_msg("[✗] Invalid selection.")
    except ValueError:
        log_msg("[✗] Invalid input.")

def cmd_install(args):
    """Full system installation, compilation, and provisioning."""
    print_header("resync - Full Arch System Replicator")

    hw = probe_system()
    pm = PackageManager()
    dm_helper = DisplayManagerHelper()

    cmd_hardware(args)

    # 1. Hostname Setup
    current_host = hw.hostname or "arch-laptop"
    if HAS_RICH:
        new_host = Prompt.ask(f"[bold cyan][?] Enter Hostname for this machine[/bold cyan]", default=current_host)
    else:
        new_host = input(f"Enter Hostname for this machine [{current_host}]: ").strip() or current_host

    # 2. Window Manager Selection
    wm_options = {
        "1": ("Umbriel (Wayland Scrolling Compositor - Built from Source)", "wm-umbriel"),
        "2": ("Hyprland (Dynamic Tiling Compositor)", "wm-hyprland"),
        "3": ("Niri (Scrollable Tiling Compositor)", "wm-niri"),
    }
    print("\n--- Select Window Manager ---")
    for k, (name, _) in wm_options.items():
        print(f" {k}) {name}")
    wm_choice = input("Select WM [1-3] (Default: 1): ").strip()
    selected_wm_name, selected_wm = wm_options.get(wm_choice, wm_options["1"])

    # 3. Display Manager Selection
    dm_options = {
        "1": ("Noctalia Greeter (Modern greetd + frosted blur)", "noctalia-greeter"),
        "2": ("SDDM (Simple SDDM Theme)", "sddm"),
        "3": ("None (Console / TTY login)", "none"),
    }
    print("\n--- Select Display Manager / Greeter ---")
    for k, (name, _) in dm_options.items():
        print(f" {k}) {name}")
    dm_choice = input("Select Display Manager [1-3] (Default: 1): ").strip()
    selected_dm_name, selected_dm = dm_options.get(dm_choice, dm_options["1"])

    # 4. Optional Package Categories
    categories = [
        ("Shell Enhancements (zsh, starship, fastfetch, lsd)", "shell.txt", True),
        ("Web Browsers", "optional-browsers.txt", True),
        ("Media & Audio Utilities", "optional-media.txt", True),
        ("CLI Utilities & Terminal Tools", "optional-cli.txt", True),
        ("Development Tools", "optional-dev.txt", True),
        ("Appearance, Fonts & Cursors", "optional-fonts.txt", True),
        ("System Maintenance & File Systems", "optional-system.txt", False),
        ("Productivity & Office", "optional-office.txt", False),
        ("DoD CAC / Smart Card Reader", "optional-cac.txt", False),
    ]

    selected_packages = set(pm.read_manifest("core.txt"))
    selected_packages.update(pm.read_manifest(f"{selected_wm}.txt"))
    selected_packages.update(dm_helper.get_dm_packages(selected_dm))

    if hw.cpu_microcode_pkg:
        selected_packages.add(hw.cpu_microcode_pkg)
    for gpu_pkg in hw.suggested_gpu_pkgs:
        selected_packages.add(gpu_pkg)

    print("\n--- Select Optional Package Groups ---")
    for cat_name, manifest_file, default_on in categories:
        default_str = "Y/n" if default_on else "y/N"
        ans = input(f"Install {cat_name}? [{default_str}]: ").strip().lower()
        if (default_on and ans != "n") or (not default_on and ans == "y"):
            selected_packages.update(pm.read_manifest(manifest_file))

    # Summary
    print_header("Installation Summary")
    print(f" • Hostname:        {new_host}")
    print(f" • Window Manager:  {selected_wm_name}")
    print(f" • Display Manager: {selected_dm_name}")
    print(f" • Total Packages:  {len(selected_packages)}")
    print(f" • Dotfile Action:  Full Templated Deployment (Zero Stow Symlinks)")

    proceed = input("\nProceed with system replication? [Y/n]: ").strip().lower()
    if proceed == "n":
        log_msg("[!] Installation aborted.")
        return

    # EXECUTION STAGE
    print_header("Executing Replication Pipeline")

    # Step A: Optimize Pacman
    pm.enable_pacman_optimizations(log_msg)

    # Step B: Set Hostname
    set_system_hostname(new_host, log_msg)

    # Step C: Separate Pacman and AUR Packages
    pacman_pkgs, aur_pkgs = pm.categorize_packages(list(selected_packages))

    # Step D: Install Official Packages
    if pacman_pkgs:
        pm.install_pacman_packages(pacman_pkgs, log_msg)

    # Step E: Build paru from source & Install AUR Packages
    if aur_pkgs:
        if not is_paru_working():
            log_msg("[*] Paru not detected or broken. Compiling paru from source...")
            build_paru_from_source(log_msg)
        pm.install_aur_packages(aur_pkgs, log_msg)

    # Step F: Build Umbriel from source if selected
    if selected_wm == "wm-umbriel":
        if not shutil.which("umbriel"):
            log_msg("[*] Umbriel binary not found. Compiling Umbriel from official source...")
            build_umbriel_from_source(log_msg)
        else:
            log_msg("[✓] Umbriel binary is already installed.")

    # Step G: Deploy Dotfiles & Assets (No Symlinks!)
    engine = DotfileEngine()
    extra_vars = {
        "BATTERY": hw.primary_battery,
        "BACKLIGHT": hw.primary_backlight,
        "HOSTNAME": new_host
    }
    engine.deploy(extra_vars=extra_vars, log_cb=log_msg)

    # Step H: Enable System Services
    enable_essential_services(is_laptop=hw.is_laptop, log_cb=log_msg)

    # Step I: Setup Display Manager
    if selected_dm != "none":
        dm_helper.setup_display_manager(selected_dm, selected_wm, log_msg)

    # Step J: Setup CAC if selected
    if any("ccid" in p or "opensc" in p for p in selected_packages):
        setup_cac_smartcard(log_msg)

    # Step K: Shell & Font Cache
    configure_user_shell("zsh", log_msg)
    refresh_font_cache(log_msg)

    print_header("Replication Complete! 🎉")
    log_msg("[✓] Your system is now an exact, clean clone with zero broken symlinks.")
    
    reboot = input("\nWould you like to reboot now? [y/N]: ").strip().lower()
    if reboot == "y":
        subprocess.run(["sudo", "systemctl", "reboot"])

def main():
    parser = argparse.ArgumentParser(
        description="resync: Modern Arch Linux System Replicator & Dotfile Sync Engine"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # install
    p_install = subparsers.add_parser("install", help="Run full system installation and replication wizard")
    
    # sync
    p_sync = subparsers.add_parser("sync", help="Fast synchronize dotfiles & configs from repo to $HOME")
    
    # diff
    p_diff = subparsers.add_parser("diff", help="Show colorized diff of local $HOME vs repo configs")
    
    # collect
    p_collect = subparsers.add_parser("collect", help="Copy modified files from $HOME back into repo configs")
    
    # hardware
    p_hw = subparsers.add_parser("hardware", help="Show detected hardware and system summary")
    
    # rollback
    p_rollback = subparsers.add_parser("rollback", help="Restore dotfiles from a previous backup generation")

    args = parser.parse_args()

    if args.command == "install":
        cmd_install(args)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "diff":
        cmd_diff(args)
    elif args.command == "collect":
        cmd_collect(args)
    elif args.command == "hardware":
        cmd_hardware(args)
    elif args.command == "rollback":
        cmd_rollback(args)
    else:
        # Default interactive behavior if run without arguments
        cmd_install(args)

if __name__ == "__main__":
    main()
