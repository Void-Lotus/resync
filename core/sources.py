#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from typing import Optional, Callable
from .hardware import get_real_user_and_home

def run_cmd(cmd, cwd=None, log_cb: Optional[Callable[[str], None]] = None, use_sudo=False) -> bool:
    """Helper to run command with streaming logs."""
    full_cmd = (["sudo"] if use_sudo else []) + cmd
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

    if proc.stdout:
        for line in proc.stdout:
            line_clean = line.rstrip()
            if log_cb:
                log_cb(line_clean)

    proc.wait()
    return proc.returncode == 0

def build_umbriel_from_source(log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Builds the Umbriel Wayland Compositor directly from its official GitHub repository:
    https://github.com/noctalia-dev/umbriel
    
    Steps:
    1. Installs build dependencies (meson, ninja, C++23 compiler, wayland, wlroots, tomlplusplus, etc.)
    2. Clones git repo and initializes SceneFX submodule
    3. Runs meson setup & compile in release mode
    4. Installs binaries to /usr/local/bin/umbriel and session files
    """
    if log_cb:
        log_cb("[*] Starting Umbriel Wayland Compositor source build pipeline...")

    # 1. Install build dependencies
    build_deps = [
        "meson", "ninja", "pkgconf", "gcc", "wayland-protocols",
        "wayland", "libxkbcommon", "libinput", "pixman", "libdrm",
        "cairo", "pango", "tomlplusplus", "nlohmann-json", "jemalloc"
    ]
    if log_cb:
        log_cb(f"[*] Ensuring {len(build_deps)} build dependencies are installed via pacman...")
    subprocess.run(["sudo", "pacman", "-S", "--needed", "--noconfirm"] + build_deps, check=False)

    build_dir = "/tmp/umbriel-source-build"
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(build_dir, exist_ok=True)

    user, home = get_real_user_and_home()
    if os.geteuid() == 0 and user != "root":
        subprocess.run(["chown", "-R", f"{user}:{user}", build_dir], check=False)

    try:
        # 2. Clone repo
        if log_cb:
            log_cb("[*] Cloning Umbriel from https://github.com/noctalia-dev/umbriel.git...")
        clone_ok = run_cmd(["git", "clone", "https://github.com/noctalia-dev/umbriel.git", "umbriel"], cwd=build_dir, log_cb=log_cb)
        if not clone_ok:
            if log_cb:
                log_cb("[✗] Failed to clone Umbriel repository.")
            return False

        repo_dir = os.path.join(build_dir, "umbriel")

        # 3. Initialize submodules (SceneFX)
        if log_cb:
            log_cb("[*] Initializing submodules (SceneFX)...")
        sub_ok = run_cmd(["git", "submodule", "update", "--init", "--recursive"], cwd=repo_dir, log_cb=log_cb)
        if not sub_ok:
            if log_cb:
                log_cb("[✗] Failed to initialize SceneFX submodules.")
            return False

        # 4. Meson configure
        if log_cb:
            log_cb("[*] Configuring build with Meson (C++23, release mode, prefix /usr/local)...")
        meson_args = [
            "meson", "setup", "build-release",
            "--prefix", "/usr/local",
            "--buildtype=release",
            "-Db_lto=true",
            "-Dcpp_std=c++23"
        ]
        cfg_ok = run_cmd(meson_args, cwd=repo_dir, log_cb=log_cb)
        if not cfg_ok:
            if log_cb:
                log_cb("[✗] Meson configuration failed.")
            return False

        # 5. Compile
        if log_cb:
            log_cb("[*] Compiling Umbriel with Meson / Ninja (this may take a couple minutes)...")
        compile_ok = run_cmd(["meson", "compile", "-C", "build-release"], cwd=repo_dir, log_cb=log_cb)
        if not compile_ok:
            if log_cb:
                log_cb("[✗] Compilation failed.")
            return False

        # 6. Install
        if log_cb:
            log_cb("[*] Installing Umbriel to /usr/local/bin...")
        inst_ok = run_cmd(["meson", "install", "-C", "build-release", "--no-rebuild"], cwd=repo_dir, log_cb=log_cb, use_sudo=True)
        if not inst_ok:
            if log_cb:
                log_cb("[✗] Meson install failed.")
            return False

        # 7. Ensure Wayland desktop session entry exists
        sess_dir = "/usr/share/wayland-sessions"
        subprocess.run(["sudo", "mkdir", "-p", sess_dir], check=False)
        desktop_entry = """[Desktop Entry]
Name=Umbriel
Comment=Umbriel Wayland Compositor
Exec=/usr/local/bin/start-umbriel
Type=Application
DesktopNames=Umbriel
"""
        p = subprocess.Popen(["sudo", "tee", f"{sess_dir}/umbriel.desktop"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
        p.communicate(input=desktop_entry.encode())

        # 8. Verify binary exists
        if shutil.which("umbriel"):
            if log_cb:
                log_cb("[✓] Umbriel Wayland Compositor built and installed successfully!")
            return True
        else:
            if log_cb:
                log_cb("[!] Binary /usr/local/bin/umbriel not found after install.")
            return False

    finally:
        shutil.rmtree(build_dir, ignore_errors=True)

if __name__ == "__main__":
    print("Testing sources module...")
    if shutil.which("umbriel"):
        print("Umbriel already installed at:", shutil.which("umbriel"))
    else:
        print("Umbriel not installed. Ready to compile.")
