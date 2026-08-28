#!/usr/bin/env python3
import os
import sys
import shutil
import difflib
import hashlib
import json
import datetime
from typing import List, Dict, Tuple, Optional, Callable

class DotfileEngine:
    """
    Direct copy, templated dotfile synchronization engine.
    Completely eliminates GNU Stow and fragile symlinks.
    Supports atomic backups, variable templating, diffing, and bidirectional sync.
    Retention policy: Keeps the last 3 backup snapshots automatically.
    """
    def __init__(self, repo_dir: Optional[str] = None, target_home: Optional[str] = None, max_backups: int = 3):
        self.repo_dir = repo_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.configs_dir = os.path.join(self.repo_dir, "configs", "home")
        self.max_backups = max_backups
        
        # Real user target home
        if target_home:
            self.target_home = target_home
        else:
            sudo_user = os.environ.get("SUDO_USER")
            if sudo_user and sudo_user != "root":
                try:
                    import pwd
                    self.target_home = pwd.getpwnam(sudo_user).pw_dir
                except Exception:
                    self.target_home = f"/home/{sudo_user}"
            else:
                self.target_home = os.environ.get("HOME", "/root")

        self.state_dir = os.path.join(self.target_home, ".local", "state", "resync")
        self.backups_dir = os.path.join(self.state_dir, "backups")
        self.generations_dir = os.path.join(self.state_dir, "generations")
        os.makedirs(self.backups_dir, exist_ok=True)
        os.makedirs(self.generations_dir, exist_ok=True)

        # Folders treated as static bulk assets for fast sync
        self.bulk_dirs = {".icons", ".themes", "Pictures/wallpapers"}

    def _file_hash(self, filepath: str) -> str:
        """Compute sha256 checksum of a file."""
        if not os.path.isfile(filepath):
            return ""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _interpolate_content(self, text: str, vars_dict: Dict[str, str]) -> str:
        """Replace {{VAR}} placeholders in text with values from vars_dict."""
        result = text
        for key, val in vars_dict.items():
            result = result.replace(f"{{{{{key}}}}}", str(val))
        return result

    def get_template_vars(self, extra_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build standard template substitution variables."""
        sudo_user = os.environ.get("SUDO_USER")
        user = sudo_user if (sudo_user and sudo_user != "root") else os.environ.get("USER", "voidlotus")
        
        hostname = ""
        if os.path.exists("/etc/hostname"):
            try:
                with open("/etc/hostname", "r") as f:
                    hostname = f.read().strip()
            except Exception:
                pass

        vars_dict = {
            "HOME": self.target_home,
            "USER": user,
            "HOSTNAME": hostname,
            "BATTERY": "BAT0",
            "BACKLIGHT": "intel_backlight",
            "SCALE": "1.0",
        }
        if extra_vars:
            vars_dict.update(extra_vars)
        return vars_dict

    def list_config_files(self) -> List[Tuple[str, str]]:
        """
        Returns list of (rel_path, abs_source_path) for dotfiles and configs (excluding huge bulk icon packs).
        """
        managed = []
        if not os.path.exists(self.configs_dir):
            return managed

        for root, dirs, files in os.walk(self.configs_dir):
            rel_root = os.path.relpath(root, self.configs_dir)
            if any(rel_root == b or rel_root.startswith(b + os.sep) for b in self.bulk_dirs):
                continue

            for file in files:
                abs_src = os.path.join(root, file)
                rel_path = os.path.relpath(abs_src, self.configs_dir)
                managed.append((rel_path, abs_src))
        return managed

    def diff(self, extra_vars: Optional[Dict[str, str]] = None) -> List[Dict[str, any]]:
        """
        Compare repo configs against live $HOME files without modifying anything.
        Returns list of diff records: {path, status, diff}.
        """
        vars_dict = self.get_template_vars(extra_vars)
        managed = self.list_config_files()
        diff_results = []

        for rel_path, abs_src in managed:
            target_path = os.path.join(self.target_home, rel_path)

            try:
                with open(abs_src, "r", encoding="utf-8") as f:
                    src_content = f.read()
                src_interpolated = self._interpolate_content(src_content, vars_dict)
            except Exception:
                src_interpolated = None

            if not os.path.lexists(target_path):
                diff_results.append({
                    "path": rel_path,
                    "status": "NEW (Not in $HOME)",
                    "diff": f"+++ File will be created: ~/{rel_path}\n"
                })
                continue

            if os.path.islink(target_path):
                diff_results.append({
                    "path": rel_path,
                    "status": "SYMLINK (Legacy Stow - will be replaced with real file)",
                    "diff": f"Legacy symlink ~/{rel_path} -> real file will replace it.\n"
                })
                continue

            if src_interpolated is None:
                if self._file_hash(abs_src) != self._file_hash(target_path):
                    diff_results.append({
                        "path": rel_path,
                        "status": "MODIFIED (Binary)",
                        "diff": f"Binary file ~/{rel_path} differs.\n"
                    })
                continue

            try:
                with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                    dst_content = f.read()
            except Exception:
                dst_content = ""

            if src_interpolated != dst_content:
                diff_lines = list(difflib.unified_diff(
                    dst_content.splitlines(keepends=True),
                    src_interpolated.splitlines(keepends=True),
                    fromfile=f"live:~/{rel_path}",
                    tofile=f"repo:{rel_path}",
                    n=3
                ))
                diff_results.append({
                    "path": rel_path,
                    "status": "MODIFIED",
                    "diff": "".join(diff_lines)
                })

        return diff_results

    def _prune_old_backups(self, keep: Optional[int] = None, log_cb: Optional[Callable[[str], None]] = None):
        """Prune old backup snapshots, retaining only the most recent N (default: 3)."""
        limit = keep if keep is not None else self.max_backups
        backups = self.list_backups()
        if len(backups) > limit:
            to_remove = backups[limit:]
            for b in to_remove:
                old_dir = os.path.join(self.backups_dir, b)
                shutil.rmtree(old_dir, ignore_errors=True)
                if log_cb:
                    log_cb(f"[*] Pruned old backup snapshot: {b}")

    def deploy(self, extra_vars: Optional[Dict[str, str]] = None, log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """
        Deploy dotfiles, scripts, wallpapers, and themes directly into $HOME.
        - Backs up existing files to ~/.local/state/resync/backups/<timestamp>/
        - Automatically prunes old backups to retain the last 3 snapshots
        - Removes any old Stow symlinks and replaces with real files
        - Interpolates variables dynamically
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_gen_dir = os.path.join(self.backups_dir, timestamp)
        vars_dict = self.get_template_vars(extra_vars)

        config_files = self.list_config_files()
        if log_cb:
            log_cb(f"[*] Deploying {len(config_files)} configurations to {self.target_home}...")

        backup_count = 0

        # 1. Deploy configs & scripts with variable interpolation
        for rel_path, abs_src in config_files:
            target_path = os.path.join(self.target_home, rel_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            if os.path.lexists(target_path):
                if os.path.islink(target_path):
                    os.unlink(target_path)
                elif os.path.isfile(target_path):
                    if self._file_hash(target_path) != self._file_hash(abs_src):
                        bck_dest = os.path.join(backup_gen_dir, rel_path)
                        os.makedirs(os.path.dirname(bck_dest), exist_ok=True)
                        shutil.copy2(target_path, bck_dest)
                        backup_count += 1

            try:
                with open(abs_src, "r", encoding="utf-8") as f:
                    content = f.read()
                interpolated = self._interpolate_content(content, vars_dict)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(interpolated)
            except UnicodeDecodeError:
                shutil.copy2(abs_src, target_path)

            if os.access(abs_src, os.X_OK):
                os.chmod(target_path, 0o755)

        # Clean up empty backup directory if no files changed
        if backup_count == 0 and os.path.exists(backup_gen_dir):
            shutil.rmtree(backup_gen_dir, ignore_errors=True)
        else:
            # Prune old backups, keeping only the last 3
            self._prune_old_backups(keep=self.max_backups, log_cb=log_cb)

        # 2. Deploy bulk assets (wallpapers, themes, icons)
        for bulk in self.bulk_dirs:
            src_bulk = os.path.join(self.configs_dir, bulk)
            dst_bulk = os.path.join(self.target_home, bulk)
            if os.path.exists(src_bulk):
                if log_cb:
                    log_cb(f"[*] Syncing assets: {bulk}...")
                os.makedirs(os.path.dirname(dst_bulk), exist_ok=True)
                if os.path.islink(dst_bulk):
                    os.unlink(dst_bulk)
                shutil.copytree(src_bulk, dst_bulk, dirs_exist_ok=True)

        # 3. Fix ownership if running under sudo
        sudo_user = os.environ.get("SUDO_USER")
        if os.geteuid() == 0 and sudo_user and sudo_user != "root":
            try:
                import pwd
                uid = pwd.getpwnam(sudo_user).pw_uid
                gid = pwd.getpwnam(sudo_user).pw_gid
                subprocess_run_chown = f"chown -R {uid}:{gid} {self.target_home}/.config {self.target_home}/.local {self.target_home}/Pictures {self.target_home}/.zshrc {self.target_home}/.bashrc"
                os.system(subprocess_run_chown)
            except Exception:
                pass

        if log_cb:
            msg = f"[✓] Deployed configurations successfully ({backup_count} files backed up)." if backup_count > 0 else "[✓] Deployed configurations successfully (all configs were already identical)."
            log_cb(msg)
        return True

    def collect(self, log_cb: Optional[Callable[[str], None]] = None) -> int:
        """
        Collect modified live files from $HOME BACK into repo configs.
        """
        config_files = self.list_config_files()
        updated_count = 0

        if log_cb:
            log_cb("[*] Collecting changes from live environment into repo configs...")

        for rel_path, abs_src in config_files:
            target_path = os.path.join(self.target_home, rel_path)
            if not os.path.exists(target_path) or os.path.islink(target_path):
                continue

            if self._file_hash(target_path) != self._file_hash(abs_src):
                os.makedirs(os.path.dirname(abs_src), exist_ok=True)
                shutil.copy2(target_path, abs_src)
                updated_count += 1
                if log_cb:
                    log_cb(f"  [+] Updated in repo: {rel_path}")

        if log_cb:
            log_cb(f"[✓] Collection complete: {updated_count} files updated in repo.")
        return updated_count

    def list_backups(self) -> List[str]:
        """List available backup timestamps sorted newest first."""
        if not os.path.exists(self.backups_dir):
            return []
        return sorted([
            d for d in os.listdir(self.backups_dir)
            if os.path.isdir(os.path.join(self.backups_dir, d))
        ], reverse=True)

    def rollback(self, timestamp: str, log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """Roll back live files from a previous backup snapshot."""
        backup_gen = os.path.join(self.backups_dir, timestamp)
        if not os.path.exists(backup_gen):
            if log_cb:
                log_cb(f"[✗] Backup snapshot '{timestamp}' does not exist.")
            return False

        if log_cb:
            log_cb(f"[*] Rolling back files from snapshot {timestamp}...")

        restored = 0
        for root, _, files in os.walk(backup_gen):
            for file in files:
                abs_bck = os.path.join(root, file)
                rel_path = os.path.relpath(abs_bck, backup_gen)
                target_path = os.path.join(self.target_home, rel_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(abs_bck, target_path)
                restored += 1

        if log_cb:
            log_cb(f"[✓] Restored {restored} files from backup {timestamp}.")
        return True

if __name__ == "__main__":
    engine = DotfileEngine()
    print("Config files tracked:", len(engine.list_config_files()))
    print("Available backups (retention: last 3):", engine.list_backups())
