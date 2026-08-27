#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from typing import List, Set, Tuple, Optional, Callable
from .aur import is_paru_working, build_paru_from_source, run_as_user

class PackageManager:
    def __init__(self, manifests_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.manifests_dir = manifests_dir or os.path.join(base_dir, "manifests")

    def read_manifest(self, filename: str) -> List[str]:
        """Read package list file, filtering out comments and whitespace."""
        filepath = os.path.join(self.manifests_dir, filename) if not os.path.isabs(filename) else filename
        if not os.path.exists(filepath):
            return []

        packages = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    packages.append(line)
        return packages

    def enable_pacman_optimizations(self, log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """Enable ParallelDownloads = 10, Color, and ILoveCandy in /etc/pacman.conf."""
        pacman_conf = "/etc/pacman.conf"
        if not os.path.exists(pacman_conf):
            return False

        if log_cb:
            log_cb("[*] Optimizing /etc/pacman.conf (ParallelDownloads = 10, Color, ILoveCandy)...")

        try:
            with open(pacman_conf, "r", encoding="utf-8") as f:
                content = f.read()

            new_lines = []
            for line in content.splitlines():
                # Enable Color
                if line.strip() == "#Color":
                    new_lines.append("Color")
                    if "ILoveCandy" not in content:
                        new_lines.append("ILoveCandy")
                # Enable ParallelDownloads
                elif line.strip().startswith("#ParallelDownloads") or (line.strip().startswith("ParallelDownloads") and "=" in line):
                    new_lines.append("ParallelDownloads = 10")
                else:
                    new_lines.append(line)

            new_content = "\n".join(new_lines) + "\n"
            p = subprocess.Popen(["sudo", "tee", pacman_conf], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
            p.communicate(input=new_content.encode())
            return p.returncode == 0
        except Exception as e:
            if log_cb:
                log_cb(f"[!] Could not optimize pacman.conf: {e}")
            return False

    def categorize_packages(self, packages: List[str]) -> Tuple[List[str], List[str]]:
        """
        Separate packages into official pacman sync repo packages and AUR packages.
        Uses pacman -Si query.
        """
        if not packages:
            return [], []

        pacman_pkgs = []
        aur_pkgs = []

        # Known AUR keywords or patterns as quick hint
        aur_suffixes = ("-git", "-bin", "-hg", "-svn", "-nightly")

        for pkg in packages:
            if pkg.endswith(aur_suffixes):
                aur_pkgs.append(pkg)
                continue

            # Check if package exists in official sync database
            try:
                res = subprocess.run(
                    ["pacman", "-Si", pkg],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
                if res.returncode == 0:
                    pacman_pkgs.append(pkg)
                else:
                    aur_pkgs.append(pkg)
            except Exception:
                aur_pkgs.append(pkg)

        return pacman_pkgs, aur_pkgs

    def install_pacman_packages(self, packages: List[str], log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """Install official repo packages using pacman."""
        if not packages:
            return True

        if log_cb:
            log_cb(f"[*] Installing {len(packages)} official pacman packages...")

        cmd = ["sudo", "pacman", "-S", "--needed", "--noconfirm"] + packages
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        if proc.stdout:
            for line in proc.stdout:
                line_clean = line.rstrip()
                if log_cb:
                    log_cb(line_clean)

        proc.wait()

        if proc.returncode == 0:
            if log_cb:
                log_cb("[✓] Pacman packages installed successfully.")
            return True
        else:
            if log_cb:
                log_cb("[!] Batch install returned non-zero code. Attempting fallback per-package installation...")
            # Fallback: install individually to not block the whole set
            failed = []
            for pkg in packages:
                res = subprocess.run(["sudo", "pacman", "-S", "--needed", "--noconfirm", pkg], capture_output=True, text=True, check=False)
                if res.returncode != 0:
                    failed.append(pkg)
            if failed and log_cb:
                log_cb(f"[!] Warning: The following pacman packages could not be installed: {', '.join(failed)}")
            return len(failed) == 0

    def install_aur_packages(self, packages: List[str], log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """Install AUR packages using paru."""
        if not packages:
            return True

        if not is_paru_working():
            if log_cb:
                log_cb("[*] Paru not detected. Compiling paru from source first...")
            if not build_paru_from_source(log_cb):
                if log_cb:
                    log_cb("[✗] Failed to build paru. Cannot proceed with AUR package installation.")
                return False

        if log_cb:
            log_cb(f"[*] Installing {len(packages)} AUR packages using paru...")

        ok, out = run_as_user(["paru", "-S", "--needed", "--noconfirm"] + packages, log_cb=log_cb)
        if ok:
            if log_cb:
                log_cb("[✓] AUR packages installed successfully.")
            return True
        else:
            if log_cb:
                log_cb("[!] Batch AUR install had issues. Attempting individual installs...")
            failed = []
            for pkg in packages:
                single_ok, _ = run_as_user(["paru", "-S", "--needed", "--noconfirm", pkg], log_cb=log_cb)
                if not single_ok:
                    failed.append(pkg)
            if failed and log_cb:
                log_cb(f"[!] Warning: The following AUR packages failed to install: {', '.join(failed)}")
            return len(failed) == 0

if __name__ == "__main__":
    pm = PackageManager()
    print("Manifests found in:", pm.manifests_dir)
    core = pm.read_manifest("core.txt")
    print(f"Core manifest packages ({len(core)}):", core[:5], "...")
