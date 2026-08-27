#!/usr/bin/env python3
import os
import glob
import subprocess
import platform
import shutil
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class HardwareSummary:
    distro_name: str = "Arch Linux"
    distro_id: str = "arch"
    is_cachyos: bool = False
    hostname: str = ""
    username: str = ""
    home_dir: str = ""
    cpu_vendor: str = "Unknown"  # "Intel", "AMD", or "Unknown"
    cpu_model: str = "Unknown"
    cpu_microcode_pkg: Optional[str] = None
    gpu_vendors: List[str] = field(default_factory=list)  # ["AMD", "NVIDIA", "Intel"]
    suggested_gpu_pkgs: List[str] = field(default_factory=list)
    is_laptop: bool = False
    battery_devices: List[str] = field(default_factory=list)
    primary_battery: str = "BAT0"
    backlight_devices: List[str] = field(default_factory=list)
    primary_backlight: str = ""

def get_real_user_and_home():
    """Detect the actual non-root user and home directory even if running under sudo."""
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        username = sudo_user
        # Try to get home from /etc/passwd or /home/<user>
        try:
            import pwd
            home_dir = pwd.getpwnam(username).pw_dir
        except Exception:
            home_dir = f"/home/{username}"
    else:
        username = os.environ.get("USER", "root")
        home_dir = os.environ.get("HOME", f"/home/{username}")
    return username, home_dir

def probe_distro() -> Dict[str, str]:
    """Read /etc/os-release to detect distro details."""
    info = {"NAME": "Arch Linux", "ID": "arch", "PRETTY_NAME": "Arch Linux"}
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        info[k] = v.strip('"\'')
        except Exception:
            pass
    return info

def probe_cpu():
    """Detect CPU vendor, model, and required microcode package."""
    vendor = "Unknown"
    model = "Unknown"
    ucode = None

    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if "vendor_id" in line and vendor == "Unknown":
                        if "AuthenticAMD" in line:
                            vendor = "AMD"
                            ucode = "amd-ucode"
                        elif "GenuineIntel" in line:
                            vendor = "Intel"
                            ucode = "intel-ucode"
                    elif "model name" in line and model == "Unknown":
                        model = line.split(":", 1)[1].strip()
                    if vendor != "Unknown" and model != "Unknown":
                        break
        except Exception:
            pass

    return vendor, model, ucode

def probe_gpus() -> (List[str], List[str]):
    """Probe PCI devices using lspci to find GPUs and suggest driver packages."""
    vendors = []
    pkgs = []

    lspci_out = ""
    if shutil.which("lspci"):
        try:
            res = subprocess.run(["lspci"], capture_output=True, text=True, check=False)
            lspci_out = res.stdout
        except Exception:
            pass

    # Search for VGA, 3D, or Display controllers
    gpu_lines = [
        line for line in lspci_out.splitlines()
        if any(term in line.lower() for term in ["vga compatible controller", "3d controller", "display controller"])
    ]

    has_nvidia = any("nvidia" in line.lower() for line in gpu_lines)
    has_amd = any("amd" in line.lower() or "advanced micro devices" in line.lower() or "ati" in line.lower() for line in gpu_lines)
    has_intel = any("intel" in line.lower() for line in gpu_lines)

    if has_amd:
        vendors.append("AMD")
        pkgs.extend(["mesa", "vulkan-radeon", "lib32-vulkan-radeon", "libva-mesa-driver"])
    if has_intel:
        vendors.append("Intel")
        pkgs.extend(["mesa", "vulkan-intel", "lib32-vulkan-intel", "intel-media-driver"])
    if has_nvidia:
        vendors.append("NVIDIA")
        # Provide nvidia-open or standard nvidia based on modern kernels
        pkgs.extend(["nvidia-open", "nvidia-utils", "lib32-nvidia-utils", "nvidia-settings"])

    return vendors, list(dict.fromkeys(pkgs))

def probe_batteries() -> (bool, List[str], str):
    """Detect battery sensors in /sys/class/power_supply/."""
    batteries = []
    for path in sorted(glob.glob("/sys/class/power_supply/BAT*")):
        name = os.path.basename(path)
        batteries.append(name)

    is_laptop = len(batteries) > 0
    primary = batteries[0] if batteries else "BAT0"
    return is_laptop, batteries, primary

def probe_backlight() -> (List[str], str):
    """Detect backlight devices in /sys/class/backlight/."""
    devices = []
    for path in sorted(glob.glob("/sys/class/backlight/*")):
        name = os.path.basename(path)
        devices.append(name)
    primary = devices[0] if devices else ""
    return devices, primary

def probe_system() -> HardwareSummary:
    """Run full hardware and system inspection and return a HardwareSummary dataclass."""
    username, home_dir = get_real_user_and_home()
    distro_info = probe_distro()
    distro_id = distro_info.get("ID", "arch").lower()
    distro_name = distro_info.get("PRETTY_NAME", distro_info.get("NAME", "Arch Linux"))
    is_cachyos = "cachyos" in distro_id or "cachyos" in distro_name.lower()

    hostname = platform.node() or ""
    if not hostname and os.path.exists("/etc/hostname"):
        try:
            with open("/etc/hostname", "r") as f:
                hostname = f.read().strip()
        except Exception:
            pass

    cpu_vendor, cpu_model, cpu_ucode = probe_cpu()
    gpu_vendors, suggested_gpu_pkgs = probe_gpus()
    is_laptop, batteries, primary_battery = probe_batteries()
    backlight_devs, primary_backlight = probe_backlight()

    return HardwareSummary(
        distro_name=distro_name,
        distro_id=distro_id,
        is_cachyos=is_cachyos,
        hostname=hostname,
        username=username,
        home_dir=home_dir,
        cpu_vendor=cpu_vendor,
        cpu_model=cpu_model,
        cpu_microcode_pkg=cpu_ucode,
        gpu_vendors=gpu_vendors,
        suggested_gpu_pkgs=suggested_gpu_pkgs,
        is_laptop=is_laptop,
        battery_devices=batteries,
        primary_battery=primary_battery,
        backlight_devices=backlight_devs,
        primary_backlight=primary_backlight
    )

if __name__ == "__main__":
    hw = probe_system()
    print("=== resync Hardware Probe ===")
    print(f"Distro:          {hw.distro_name} (ID: {hw.distro_id}, CachyOS: {hw.is_cachyos})")
    print(f"User:            {hw.username} (Home: {hw.home_dir})")
    print(f"Hostname:        {hw.hostname}")
    print(f"CPU:             {hw.cpu_model} ({hw.cpu_vendor}, ucode: {hw.cpu_microcode_pkg})")
    print(f"GPUs:            {', '.join(hw.gpu_vendors) if hw.gpu_vendors else 'None detected'}")
    print(f"Chassis:         {'Laptop' if hw.is_laptop else 'Desktop'}")
    if hw.is_laptop:
        print(f"Batteries:       {', '.join(hw.battery_devices)} (Primary: {hw.primary_battery})")
        print(f"Backlight:       {', '.join(hw.backlight_devices)} (Primary: {hw.primary_backlight})")
