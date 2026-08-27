#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from typing import Optional, Callable
from .hardware import get_real_user_and_home

def setup_cac_smartcard(log_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Setup DoD Common Access Card (CAC) / Smart Card support.
    Enables pcscd service and registers OpenSC PKCS#11 module into NSS databases.
    """
    if log_cb:
        log_cb("[*] Setting up DoD CAC smart card services...")

    # 1. Enable pcscd daemon
    subprocess.run(["sudo", "systemctl", "enable", "--now", "pcscd.socket"], check=False)
    subprocess.run(["sudo", "systemctl", "enable", "--now", "pcscd.service"], check=False)

    # 2. Register OpenSC PKCS#11 module in user NSS DB (for Chromium, Zen, Chrome)
    user, home = get_real_user_and_home()
    pki_nssdb = os.path.join(home, ".pki", "nssdb")
    os.makedirs(pki_nssdb, exist_ok=True)

    if shutil.which("modutil"):
        if log_cb:
            log_cb(f"[*] Registering OpenSC PKCS#11 module into {pki_nssdb}...")
        
        # Check if already registered
        list_res = subprocess.run(
            ["modutil", "-list", "-dbdir", f"sql:{pki_nssdb}"],
            capture_output=True, text=True, check=False
        )
        if "OpenSC" not in list_res.stdout:
            opensc_lib = "/usr/lib/opensc-pkcs11.so"
            if os.path.exists(opensc_lib):
                cmd_add = [
                    "modutil", "-add", "OpenSC PKCS#11",
                    "-libfile", opensc_lib,
                    "-dbdir", f"sql:{pki_nssdb}",
                    "-force"
                ]
                subprocess.run(cmd_add, capture_output=True, check=False)

    if log_cb:
        log_cb("[✓] DoD CAC smart card setup completed.")
    return True
