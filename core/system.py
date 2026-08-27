#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from typing import List, Optional, Callable
from .hardware import get_real_user_and_home

def set_system_hostname(new_hostname: str, log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Set system hostname using hostnamectl and update /etc/hostname and /etc/hosts.
    """
    if not new_hostname:
        return False

    new_hostname = new_hostname.strip()
    if log_cb:
        log_cb(f"[*] Setting system hostname to '{new_hostname}'...")

    # 1. Update /etc/hostname
    try:
        p = subprocess.Popen(["sudo", "tee", "/etc/hostname"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
        p.communicate(input=f"{new_hostname}\n".encode())
    except Exception as e:
        if log_cb:
            log_cb(f"[!] Warning updating /etc/hostname: {e}")

    # 2. Update /etc/hosts
    hosts_path = "/etc/hosts"
    hosts_content = f"""# Static table lookup for hostnames.
#<ip-address>	<hostname.domain.org>	<hostname>
127.0.0.1	localhost
::1		localhost
127.0.1.1	{new_hostname}.localdomain	{new_hostname}
"""
    try:
        p = subprocess.Popen(["sudo", "tee", hosts_path], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
        p.communicate(input=hosts_content.encode())
    except Exception as e:
        if log_cb:
            log_cb(f"[!] Warning updating /etc/hosts: {e}")

    # 3. Apply via hostnamectl if systemd is running
    try:
        subprocess.run(["sudo", "hostnamectl", "set-hostname", new_hostname], check=False)
    except Exception:
        pass

    if log_cb:
        log_cb(f"[✓] Hostname set to '{new_hostname}'.")
    return True

def enable_essential_services(is_laptop: bool = False, log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Enable standard systemd services for networking, bluetooth, power, and audio.
    """
    services = [
        "NetworkManager.service",
        "bluetooth.service",
    ]

    if is_laptop:
        # Check power management services
        if shutil.which("power-profiles-daemon"):
            services.append("power-profiles-daemon.service")
        elif shutil.which("tlp"):
            services.append("tlp.service")

    if log_cb:
        log_cb(f"[*] Enabling {len(services)} system services...")

    for svc in services:
        if log_cb:
            log_cb(f"  -> systemctl enable --now {svc}")
        subprocess.run(["sudo", "systemctl", "enable", "--now", svc], capture_output=True, check=False)

    if log_cb:
        log_cb("[✓] System services configured.")
    return True

def configure_user_shell(shell_name: str = "zsh", log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Set default login shell for the non-root user (e.g. /usr/bin/zsh).
    """
    username, _ = get_real_user_and_home()
    shell_path = shutil.which(shell_name)
    if not shell_path:
        if log_cb:
            log_cb(f"[!] Shell '{shell_name}' not found in PATH.")
        return False

    if log_cb:
        log_cb(f"[*] Setting default shell for '{username}' to {shell_path}...")

    res = subprocess.run(["sudo", "chsh", "-s", shell_path, username], capture_output=True, text=True, check=False)
    if res.returncode == 0:
        if log_cb:
            log_cb(f"[✓] Default shell changed to {shell_name}.")
        return True
    else:
        if log_cb:
            log_cb(f"[!] Could not change default shell: {res.stderr}")
        return False

def refresh_font_cache(log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """Run fc-cache -fv to register new fonts."""
    if shutil.which("fc-cache"):
        if log_cb:
            log_cb("[*] Refreshing system and user font cache (fc-cache)...")
        res = subprocess.run(["fc-cache", "-fv"], capture_output=True, text=True, check=False)
        if log_cb:
            log_cb("[✓] Font cache refreshed.")
        return res.returncode == 0
    return False

if __name__ == "__main__":
    print("Testing system module...")
    user, home = get_real_user_and_home()
    print(f"Target user: {user} ({home})")
