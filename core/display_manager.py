#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from typing import Optional, Callable
from .hardware import get_real_user_and_home

class DisplayManagerHelper:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sys_configs = os.path.join(self.base_dir, "configs", "system")

    def get_dm_packages(self, choice: str):
        """Returns list of packages required for the chosen display manager."""
        if choice == "noctalia-greeter":
            return ["greetd", "noctalia-greeter", "accountsservice", "polkit", "dbus"]
        elif choice == "sddm":
            return ["sddm", "qt5-graphicaleffects", "qt5-quickcontrols2", "qt5-svg"]
        return []

    def setup_display_manager(self, choice: str, selected_wm: str = "wm-umbriel", log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """Configure and enable the chosen display manager."""
        if choice == "noctalia-greeter":
            return self.setup_noctalia_greeter(selected_wm, log_cb)
        elif choice == "sddm":
            return self.setup_sddm(log_cb)
        elif choice == "none":
            if log_cb:
                log_cb("[*] Skipping Display Manager installation (Console TTY login).")
            return True
        return False

    def setup_noctalia_greeter(self, selected_wm: str = "wm-umbriel", log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """Setup Noctalia Greeter via greetd, accounts-daemon, and polkit."""
        if log_cb:
            log_cb("[*] Configuring Noctalia Greeter (greetd)...")

        wm_session_map = {
            "wm-umbriel": "Umbriel",
            "wm-hyprland": "hyprland",
            "wm-niri": "niri",
            "Umbriel": "Umbriel",
            "Hyprland": "hyprland",
            "Niri": "niri"
        }
        session_name = wm_session_map.get(selected_wm, "Umbriel")

        # 1. Enable accounts-daemon
        subprocess.run(["sudo", "systemctl", "enable", "--now", "accounts-daemon.service"], check=False)

        # 2. Greeter directory permissions
        greeter_dir = "/var/lib/noctalia-greeter"
        subprocess.run(["sudo", "mkdir", "-p", greeter_dir], check=False)
        subprocess.run(["sudo", "chown", "-R", "greeter:greeter", greeter_dir], check=False)

        # 3. Deploy declarative greeter.toml if present
        src_greeter_toml = os.path.join(self.sys_configs, "noctalia-greeter", "greeter.toml")
        if os.path.exists(src_greeter_toml):
            subprocess.run(["sudo", "cp", src_greeter_toml, f"{greeter_dir}/greeter.toml"], check=False)
            subprocess.run(["sudo", "chown", "greeter:greeter", f"{greeter_dir}/greeter.toml"], check=False)
            subprocess.run(["sudo", "chmod", "644", f"{greeter_dir}/greeter.toml"], check=False)

        # 4. Polkit rule
        polkit_src = os.path.join(self.sys_configs, "noctalia-greeter", "50-noctalia-greeter.rules")
        if os.path.exists(polkit_src):
            subprocess.run(["sudo", "mkdir", "-p", "/etc/polkit-1/rules.d"], check=False)
            subprocess.run(["sudo", "cp", polkit_src, "/etc/polkit-1/rules.d/50-noctalia-greeter.rules"], check=False)
            subprocess.run(["sudo", "chmod", "644", "/etc/polkit-1/rules.d/50-noctalia-greeter.rules"], check=False)

        # 5. AccountsService Avatar
        user, home = get_real_user_and_home()
        avatar_paths = [
            os.path.join(home, "Pictures", "wallpapers", "GlitchLotus.png"),
            os.path.join(self.base_dir, "configs", "home", "Pictures", "wallpapers", "GlitchLotus.png")
        ]
        avatar_src = next((p for p in avatar_paths if os.path.exists(p)), None)
        if avatar_src:
            subprocess.run(["sudo", "mkdir", "-p", "/var/lib/AccountsService/icons"], check=False)
            subprocess.run(["sudo", "mkdir", "-p", "/var/lib/AccountsService/users"], check=False)
            icon_dst = f"/var/lib/AccountsService/icons/{user}"
            subprocess.run(["sudo", "cp", avatar_src, icon_dst], check=False)
            subprocess.run(["sudo", "chmod", "644", icon_dst], check=False)

            user_meta = f"[User]\nIcon={icon_dst}\nSession={session_name}\nSystemAccount=false\n"
            meta_path = f"/var/lib/AccountsService/users/{user}"
            p = subprocess.Popen(["sudo", "tee", meta_path], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
            p.communicate(input=user_meta.encode())
            subprocess.run(["sudo", "chmod", "600", meta_path], check=False)

        # 6. Greetd config
        subprocess.run(["sudo", "mkdir", "-p", "/etc/greetd"], check=False)
        greetd_conf = f"""[terminal]
vt = 1

[default_session]
command = "/usr/bin/noctalia-greeter-session -- --session {session_name}"
user = "greeter"
"""
        p = subprocess.Popen(["sudo", "tee", "/etc/greetd/config.toml"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
        p.communicate(input=greetd_conf.encode())

        # 7. Disable competing DMs and enable greetd
        for dm in ["sddm.service", "gdm.service", "lightdm.service"]:
            subprocess.run(["sudo", "systemctl", "disable", dm], stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["sudo", "systemctl", "enable", "greetd.service"], check=False)

        if log_cb:
            log_cb("[✓] Noctalia Greeter (greetd) enabled successfully.")
        return True

    def setup_sddm(self, log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """Setup SDDM Display Manager."""
        if log_cb:
            log_cb("[*] Configuring SDDM Display Manager...")

        sddm_src = os.path.join(self.sys_configs, "sddm")
        if os.path.exists(sddm_src):
            subprocess.run(["sudo", "mkdir", "-p", "/usr/share/sddm/themes"], check=False)
            subprocess.run(["sudo", "cp", "-r", sddm_src, "/usr/share/sddm/themes/simple_sddm_2"], check=False)

        subprocess.run(["sudo", "mkdir", "-p", "/etc/sddm.conf.d"], check=False)
        sddm_conf = "[Theme]\nCurrent=simple_sddm_2\n"
        p = subprocess.Popen(["sudo", "tee", "/etc/sddm.conf.d/kde_settings.conf"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
        p.communicate(input=sddm_conf.encode())

        for dm in ["greetd.service", "gdm.service", "lightdm.service"]:
            subprocess.run(["sudo", "systemctl", "disable", dm], stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["sudo", "systemctl", "enable", "sddm.service"], check=False)

        if log_cb:
            log_cb("[✓] SDDM enabled successfully.")
        return True
