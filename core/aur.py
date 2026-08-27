#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from typing import Callable, Optional

def get_real_user():
    """Detect the non-root username even if running under sudo."""
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        return sudo_user
    return os.environ.get("USER", "root")

def run_as_user(cmd, cwd=None, log_cb: Optional[Callable[[str], None]] = None):
    """Run a command as the normal non-root user (since makepkg/paru cannot run as root)."""
    current_user = get_real_user()
    is_root = (os.geteuid() == 0)

    if is_root and current_user != "root":
        full_cmd = ["sudo", "-u", current_user] + cmd
    else:
        full_cmd = cmd

    if log_cb:
        log_cb(f"Executing: {' '.join(full_cmd)}")

    proc = subprocess.Popen(
        full_cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    output_lines = []
    if proc.stdout:
        for line in proc.stdout:
            line_clean = line.rstrip()
            output_lines.append(line_clean)
            if log_cb:
                log_cb(line_clean)

    proc.wait()
    return proc.returncode == 0, "\n".join(output_lines)

def is_paru_working() -> bool:
    """Check if paru is installed AND executable without dynamic library (libalpm) errors."""
    paru_path = shutil.which("paru")
    if not paru_path:
        return False
    try:
        res = subprocess.run(["paru", "--version"], capture_output=True, text=True, check=False)
        return res.returncode == 0
    except Exception:
        return False

def ensure_build_prerequisites(log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """Ensure base-devel, git, rust, and cargo are installed via pacman."""
    if log_cb:
        log_cb("[*] Checking and installing build prerequisites (base-devel, git, rust, cargo)...")

    cmd = ["sudo", "pacman", "-S", "--needed", "--noconfirm", "base-devel", "git", "rust", "cargo"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        if log_cb:
            log_cb(f"[!] Warning during prerequisite installation: {res.stderr}")
        return False
    if log_cb:
        log_cb("[✓] Build prerequisites are ready.")
    return True

def build_paru_from_source(log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Clone and build paru directly from source (https://aur.archlinux.org/paru.git).
    Building from source ensures paru links against the currently installed libalpm version,
    preventing breakages during upstream pacman updates.
    """
    if is_paru_working():
        if log_cb:
            log_cb("[✓] Paru is already installed and functional.")
        return True

    if log_cb:
        log_cb("[*] Preparing to compile paru from source...")

    # 1. Ensure compilation dependencies exist
    ensure_build_prerequisites(log_cb)

    build_dir = "/tmp/paru-source-build"
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(build_dir, exist_ok=True)

    # Ensure build_dir is owned by the user
    real_user = get_real_user()
    if os.geteuid() == 0 and real_user != "root":
        subprocess.run(["chown", "-R", f"{real_user}:{real_user}", build_dir], check=False)

    try:
        # 2. Clone paru source from AUR
        if log_cb:
            log_cb("[*] Cloning paru from https://aur.archlinux.org/paru.git...")
        clone_ok, clone_out = run_as_user(["git", "clone", "https://aur.archlinux.org/paru.git", "paru"], cwd=build_dir, log_cb=log_cb)
        if not clone_ok:
            if log_cb:
                log_cb(f"[✗] Failed to clone paru repo: {clone_out}")
            return False

        paru_pkg_dir = os.path.join(build_dir, "paru")

        # 3. Compile and install with makepkg -si
        if log_cb:
            log_cb("[*] Compiling paru with makepkg (this may take a couple minutes)...")
        make_ok, make_out = run_as_user(["makepkg", "-si", "--noconfirm"], cwd=paru_pkg_dir, log_cb=log_cb)

        if not make_ok:
            if log_cb:
                log_cb(f"[✗] Failed to compile paru: {make_out}")
            return False

        # 4. Verify installation
        if is_paru_working():
            if log_cb:
                log_cb("[✓] Paru successfully built and installed from source!")
            return True
        else:
            if log_cb:
                log_cb("[✗] Paru installation completed but binary test failed.")
            return False

    finally:
        shutil.rmtree(build_dir, ignore_errors=True)

if __name__ == "__main__":
    print("Testing AUR helper detection...")
    working = is_paru_working()
    print(f"Paru working: {working}")
    if not working:
        print("Building paru from source...")
        build_paru_from_source(print)
